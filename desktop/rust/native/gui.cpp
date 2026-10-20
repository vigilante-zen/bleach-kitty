#include <QtNetwork>
#include <QtSvg/QSvgRenderer>
#include <QtWidgets>
#include <cstring>
#include <stdexcept>
extern "C" char *bankai_request(const char *);
extern "C" void bankai_free(char *);
extern "C" bool bankai_hash_file(const char *path, unsigned char *output) {
  QFile file(QString::fromUtf8(path));
  if (!file.open(QIODevice::ReadOnly))
    return false;
  QCryptographicHash hash(QCryptographicHash::Sha256);
  if (!hash.addData(&file))
    return false;
  auto hex = hash.result().toHex();
  std::memcpy(output, hex.constData(), 64);
  output[64] = 0;
  return true;
}
extern "C" size_t bankai_timestamp(unsigned char *output, size_t capacity) {
  auto stamp =
      QDateTime::currentDateTime().toString("yyyyMMdd-HHmmss").toUtf8();
  auto length = std::min(capacity, size_t(stamp.size()));
  std::memcpy(output, stamp.constData(), length);
  return length;
}
extern "C" void bankai_hash_bytes(const unsigned char *data, size_t length,
                                  unsigned char *output) {
  auto hex = QCryptographicHash::hash(
                 QByteArrayView(reinterpret_cast<const char *>(data), length),
                 QCryptographicHash::Sha256)
                 .toHex();
  std::memcpy(output, hex.constData(), 64);
  output[64] = 0;
}

static QJsonValue rpc(const QJsonObject &request) {
  auto bytes = QJsonDocument(request).toJson(QJsonDocument::Compact);
  char *answer = bankai_request(bytes.constData());
  auto object = QJsonDocument::fromJson(QByteArray(answer)).object();
  bankai_free(answer);
  if (!object.value("ok").toBool())
    throw std::runtime_error(
        object.value("error").toString("Invalid Rust response").toStdString());
  return object.value("result");
}
static QString sizeText(double bytes) {
  QStringList units{"B", "KiB", "MiB", "GiB", "TiB"};
  int i = 0;
  while (bytes >= 1024 && i < 4) {
    bytes /= 1024;
    ++i;
  }
  return QString::number(bytes, 'f', 1) + " " + units[i];
}
static QLabel *label(const QString &text, const QString &name = {}) {
  auto *w = new QLabel(text);
  w->setWordWrap(true);
  w->setObjectName(name);
  return w;
}
static QIcon svgIcon(QByteArray source, const QString &accent = {}) {
  if (!accent.isEmpty())
    source.replace("#d72f43", accent.toUtf8());
  QSvgRenderer renderer(source);
  QIcon icon;
  if (!renderer.isValid())
    return icon;
  for (int size : {16, 22, 24, 32, 48, 64, 128}) {
    QPixmap image(size, size);
    image.fill(Qt::transparent);
    QPainter painter(&image);
    renderer.render(&painter);
    painter.end();
    icon.addPixmap(image);
  }
  return icon;
}
class Artwork : public QWidget {
public:
  QPixmap image;
  QJsonObject preset;
  Artwork() { setMinimumHeight(200); }
  void select(const QJsonObject &p, const QString &wallpapers) {
    preset = p;
    image = QPixmap(wallpapers + "/" + p.value("image").toString());
    update();
  }

protected:
  void paintEvent(QPaintEvent *) override {
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing);
    QPainterPath clip;
    clip.addRoundedRect(QRectF(rect()), 12, 12);
    painter.setClipPath(clip);
    painter.fillRect(rect(), QColor("#111925"));
    if (!image.isNull()) {
      auto scaled =
          image.scaled(size(), Qt::KeepAspectRatio, Qt::SmoothTransformation);
      painter.drawPixmap((width() - scaled.width()) / 2,
                         (height() - scaled.height()) / 2, scaled);
    }
    QLinearGradient gradient(0, height() * .25, 0, height());
    gradient.setColorAt(0, QColor(9, 12, 18, 0));
    gradient.setColorAt(1, QColor(9, 12, 18, 245));
    painter.fillRect(rect(), gradient);
    painter.setPen(QColor(preset.value("accent").toString()));
    QFont font("Noto Sans", 10);
    font.setLetterSpacing(QFont::AbsoluteSpacing, 3);
    painter.setFont(font);
    painter.drawText(24, height() - 77,
                     "SOUL SOCIETY / " +
                         preset.value("title").toString().toUpper());
    painter.setPen(Qt::white);
    painter.setFont(QFont("Noto Sans", 25, QFont::Bold));
    painter.drawText(22, height() - 37, preset.value("title").toString());
    painter.setFont(QFont("Noto Sans", 10));
    painter.setPen(QColor("#bcc9da"));
    painter.drawText(24, height() - 15, preset.value("subtitle").toString());
  }
};

class Window : public QMainWindow {
public:
  QJsonObject bootstrap;
  QJsonArray presets;
  QString home, data, wallpapers, selected, trayPreset;
  QListWidget *navigation;
  QStackedWidget *pages;
  Artwork *art;
  QLabel *saved, *notice, *previewNote, *storage, *snapshotDetails;
  QComboBox *snapshots, *portraitChoice, *portraitArt;
  QSpinBox *keep;
  QCheckBox *autostart, *matchDesktop;
  QLabel *portraitPreview, *mangaPreview, *portraitCaption;
  QString savedDesktop;
  QPushButton *verifyButton, *restoreButton, *protectButton, *cleanupButton,
      *logButton;
  QPlainTextEdit *log;
  QMap<QString, QToolButton *> cards;
  QList<QPushButton *> buttons;
  QMap<QString, QJsonObject> rows;
  QMap<QString, QAction *> presetActions;
  QList<QAction *> taskActions;
  QSystemTrayIcon *tray = nullptr;
  QMenu *trayMenu = nullptr;
  QAction *trayStatus = nullptr;
  QProcess *process = nullptr;
  QByteArray output;
  QFileSystemWatcher watcher;
  QTimer debounce, poll, slowTimer;
  bool quitting = false;
  Window() {
    bootstrap = rpc({{"op", "bootstrap"}}).toObject();
    presets = bootstrap.value("presets").toArray();
    home = bootstrap.value("home").toString();
    data = bootstrap.value("data").toString();
    wallpapers = home + "/Pictures/Bleach-TYBW/Wallpapers";
    qApp->setStyleSheet(bootstrap.value("style").toString());
    setWindowTitle("Bankai Rust · Soul Society Control Center");
    setWindowIcon(svgIcon(bootstrap.value("mask_svg").toString().toUtf8()));
    setMinimumSize(850, 590);
    auto screen = QGuiApplication::primaryScreen()->availableGeometry();
    resize(qMin(1140, int(screen.width() * .93)),
           qMin(820, int(screen.height() * .93)));
    auto *body = new QWidget;
    setCentralWidget(body);
    auto *layout = new QHBoxLayout(body);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(0);
    auto *sidebar = new QFrame;
    sidebar->setObjectName("sidebar");
    sidebar->setFixedWidth(210);
    auto *side = new QVBoxLayout(sidebar);
    side->setContentsMargins(23, 30, 23, 23);
    side->addWidget(label("SOUL SOCIETY", "eyebrow"));
    side->addWidget(label("BANKAI", "brand"));
    side->addWidget(label("Rust edition · 0.1", "muted"));
    side->addSpacing(28);
    navigation = new QListWidget;
    navigation->addItems(
        {"Appearance", "Backups & restore", "Terminal & tools"});
    side->addWidget(navigation);
    saved = label("", "muted");
    side->addWidget(saved);
    side->addSpacing(10);
    side->addWidget(label("THOUSAND-YEAR\nBLOOD WAR", "eyebrow"));
    layout->addWidget(sidebar);
    auto *content = new QWidget;
    auto *right = new QVBoxLayout(content);
    right->setContentsMargins(26, 25, 26, 18);
    right->setSpacing(13);
    pages = new QStackedWidget;
    pages->addWidget(appearancePage());
    pages->addWidget(backupsPage());
    pages->addWidget(toolsPage());
    right->addWidget(pages, 1);
    notice =
        label("Ready. Rust controls your presets and snapshots.", "notice");
    right->addWidget(notice);
    logButton = new QPushButton("Show activity");
    logButton->setMaximumWidth(140);
    right->addWidget(logButton);
    log = new QPlainTextEdit;
    log->setReadOnly(true);
    log->setMaximumHeight(110);
    log->hide();
    right->addWidget(log);
    connect(logButton, &QPushButton::clicked, this, [this] {
      log->setVisible(!log->isVisible());
      logButton->setText(log->isVisible() ? "Hide activity" : "Show activity");
    });
    layout->addWidget(content, 1);
    connect(navigation, &QListWidget::currentRowChanged, pages,
            &QStackedWidget::setCurrentIndex);
    navigation->setCurrentRow(0);
    slowTimer.setSingleShot(true);
    slowTimer.setInterval(120000);
    connect(&slowTimer, &QTimer::timeout, this, [this] {
      notice->setText(
          "The action is still running. See activity for progress.");
      log->show();
    });
    debounce.setSingleShot(true);
    debounce.setInterval(150);
    connect(&debounce, &QTimer::timeout, this, [this] { refreshStatus(); });
    connect(&watcher, &QFileSystemWatcher::fileChanged, this,
            [this] { debounce.start(); });
    connect(&watcher, &QFileSystemWatcher::directoryChanged, this,
            [this] { debounce.start(); });
    if (QDir(data).exists())
      watcher.addPath(data);
    poll.setInterval(30000);
    connect(&poll, &QTimer::timeout, this, [this] { refreshStatus(); });
    poll.start();
    refreshStatus();
    selectPreset(
        rpc({{"op", "status"}}).toObject().value("current").toString("tybw"));
    refreshSnapshots();
  }
  QPushButton *button(const QString &text, std::function<void()> fn,
                      bool primary = false) {
    auto *b = new QPushButton(text);
    if (primary)
      b->setObjectName("primary");
    connect(b, &QPushButton::clicked, this, std::move(fn));
    buttons.append(b);
    return b;
  }
  QJsonObject preset(const QString &id) const {
    for (auto p : presets)
      if (p.toObject().value("id").toString() == id)
        return p.toObject();
    return presets.first().toObject();
  }
  void selectPreset(const QString &id) {
    if (!cards.contains(id))
      return;
    selected = id;
    cards[id]->setChecked(true);
    auto p = preset(id);
    art->select(p, wallpapers);
    previewNote->setText("Previewing " + p.value("title").toString() +
                         ". Applying saves a snapshot first.");
  }
  QWidget *appearancePage() {
    auto *page = new QWidget;
    auto *layout = new QVBoxLayout(page);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(13);
    layout->addWidget(label("Make it yours", "heading"));
    layout->addWidget(
        label("Matching wallpaper, lock screen and desktop colors. "
              "Four presets fit your 21:9 monitors.",
              "muted"));
    art = new Artwork;
    layout->addWidget(art, 1);
    auto *grid = new QGridLayout;
    auto *group = new QButtonGroup(this);
    group->setExclusive(true);
    int i = 0;
    for (auto item : presets) {
      auto p = item.toObject();
      auto id = p.value("id").toString();
      auto *card = new QToolButton;
      card->setCheckable(true);
      card->setToolButtonStyle(Qt::ToolButtonTextUnderIcon);
      card->setText(p.value("title").toString());
      card->setToolTip(p.value("subtitle").toString());
      QImageReader reader(wallpapers + "/" + p.value("image").toString());
      reader.setScaledSize(reader.size().scaled(138, 65, Qt::KeepAspectRatio));
      card->setIcon(QIcon(QPixmap::fromImage(reader.read())));
      card->setIconSize(QSize(138, 65));
      card->setMinimumHeight(96);
      connect(card, &QToolButton::clicked, this,
              [this, id] { selectPreset(id); });
      group->addButton(card);
      cards[id] = card;
      grid->addWidget(card, i / 4, i % 4);
      ++i;
    }
    layout->addLayout(grid);
    previewNote = label("", "muted");
    layout->addWidget(previewNote);
    auto *actions = new QHBoxLayout;
    actions->addWidget(button(
        "Apply preset",
        [this] {
          startTask({{"op", "apply"}, {"preset", selected}},
                    "Applying preset…");
        },
        true));
    actions->addWidget(button("Open wallpaper", [this] {
      openFile(wallpapers + "/" + preset(selected).value("image").toString());
    }));
    actions->addStretch();
    layout->addLayout(actions);
    auto *scroll = new QScrollArea;
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    scroll->setWidget(page);
    return scroll;
  }
  QWidget *backupsPage() {
    auto *page = new QWidget;
    auto *layout = new QVBoxLayout(page);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(16);
    layout->addWidget(label("Keep a way back", "heading"));
    layout->addWidget(label("Compatible snapshots, verified restores, and "
                            "protection for your favorites.",
                            "muted"));
    layout->addWidget(button(
        "Create snapshot",
        [this] { startTask({{"op", "backup"}}, "Creating snapshot…"); }, true));
    layout->addSpacing(8);
    layout->addWidget(label("SAVED SNAPSHOTS", "eyebrow"));
    snapshots = new QComboBox;
    layout->addWidget(snapshots);
    snapshotDetails = label("", "muted");
    layout->addWidget(snapshotDetails);
    storage = label("", "notice");
    layout->addWidget(storage);
    connect(snapshots, &QComboBox::currentIndexChanged, this,
            [this] { snapshotChanged(); });
    auto *row = new QHBoxLayout;
    verifyButton = button("Verify", [this] {
      startTask(
          {{"op", "verify"}, {"name", snapshots->currentData().toString()}},
          "Verifying snapshot…");
    });
    row->addWidget(verifyButton);
    restoreButton = button("Restore…", [this] { restoreSelected(); });
    row->addWidget(restoreButton);
    protectButton = button("Protect snapshot", [this] {
      auto name = snapshots->currentData().toString();
      startTask({{"op", "protect"},
                 {"name", name},
                 {"enabled", !rows[name].value("protected").toBool()}},
                "Updating protection…");
    });
    row->addWidget(protectButton);
    row->addWidget(button("Refresh", [this] { refreshSnapshots(); }));
    layout->addLayout(row);
    layout->addSpacing(8);
    layout->addWidget(label("CLEAN UP OLDER COPIES", "eyebrow"));
    auto *cleanup = new QHBoxLayout;
    cleanup->addWidget(label("Keep newest"));
    keep = new QSpinBox;
    keep->setRange(1, 100);
    keep->setValue(5);
    cleanup->addWidget(keep);
    cleanup->addWidget(label("plus all protected snapshots"));
    cleanup->addStretch();
    cleanupButton = button("Preview cleanup…", [this] { previewCleanup(); });
    cleanup->addWidget(cleanupButton);
    layout->addLayout(cleanup);
    layout->addStretch();
    layout->addWidget(label("After restoring, log out and back in. The system "
                            "login screen uses its separate setup guide.",
                            "notice"));
    return page;
  }
  QWidget *toolsPage() {
    auto *page = new QWidget;
    auto *layout = new QVBoxLayout(page);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(13);
    layout->addWidget(label("At your command", "heading"));
    layout->addWidget(label(
        "Your existing portraits, favorites, greetings and monitor.", "muted"));
    layout->addWidget(label("TERMINAL ARTWORK", "eyebrow"));
    portraitChoice = new QComboBox;
    portraitChoice->setAccessibleName("Terminal character");
    portraitChoice->addItem("Random characters", "random");
    layout->addWidget(portraitChoice);
    matchDesktop = new QCheckBox("Match desktop character");
    layout->addWidget(matchDesktop);
    portraitArt = new QComboBox;
    portraitArt->setAccessibleName("Portrait art style");
    portraitArt->addItem("Color", "color");
    portraitArt->addItem("Manga", "manga");
    portraitArt->addItem("Mixed color and manga", "mixed");
    layout->addWidget(portraitArt);
    auto *previewRow = new QHBoxLayout;
    portraitPreview = new QLabel;
    mangaPreview = new QLabel;
    for (auto *image : {portraitPreview, mangaPreview}) {
      image->setFixedSize(180, 180);
      image->setAlignment(Qt::AlignCenter);
      previewRow->addWidget(image);
    }
    previewRow->addStretch();
    layout->addLayout(previewRow);
    portraitCaption = label("", "muted");
    layout->addWidget(portraitCaption);
    connect(portraitChoice, &QComboBox::currentIndexChanged, this, [this] { updatePortraitPreview(); });
    connect(portraitArt, &QComboBox::currentIndexChanged, this, [this] { updatePortraitPreview(); });
    connect(matchDesktop, &QCheckBox::toggled, this, [this] { updatePortraitPreview(); });
    layout->addWidget(button("Save terminal artwork", [this] {
      startTask({{"op", "save-portraits"},
                 {"choice", portraitChoice->currentData().toString()},
                 {"art", portraitArt->currentData().toString()},
                 {"match_desktop", matchDesktop->isChecked()}},
                "Saving terminal artwork…");
    }, true));
    layout->addWidget(label("Applies to new terminal tabs. Enable matching to follow desktop presets. "
                            "Random uses your existing groups and favorites. "
                            "Color fills in when manga is unavailable.", "muted"));
    layout->addWidget(button(
        "Terminal settings",
        [this] { terminal("bankai-settings", "Bankai settings"); }, true));
    layout->addWidget(button("Soul Society Terminal", [this] { terminal(); }));
    layout->addWidget(button("Reiatsu Monitor", [this] {
      terminal("bankai-monitor", "Reiatsu Monitor");
    }));
    layout->addWidget(button("Check setup", [this] {
      terminal("bankai-doctor; read -P 'Press Enter to close'",
               "Bankai diagnostics");
    }));
    layout->addWidget(button("Browse artwork", [this] {
      openFile(home + "/.config/fastfetch/previews/manga-roster.html");
    }));
    layout->addWidget(button("Login screen setup", [this] { loginSetup(); }));
    layout->addWidget(button("Setup & restore guide",
                             [this] { openFile(data + "/README.md"); }));
    autostart = new QCheckBox("Start the Rust edition in the tray at login");
    layout->addWidget(autostart);
    connect(autostart, &QCheckBox::toggled, this, [this](bool enabled) {
      startTask({{"op", "autostart"}, {"enabled", enabled}},
                "Saving startup preference…");
    });
    layout->addWidget(label("The Python edition keeps its own login-startup "
                            "preference. Choose the edition you want to run.",
                            "muted"));
    layout->addStretch();
    auto *scroll = new QScrollArea;
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    scroll->setWidget(page);
    return scroll;
  }
  void updatePortraitPreview() {
    portraitChoice->setEnabled(!process && !matchDesktop->isChecked());
    auto choice = portraitChoice->currentData().toString();
    if (matchDesktop->isChecked())
      choice = preset(savedDesktop).value("portrait").toString();
    bool sample = choice == "random";
    if (sample)
      choice = portraitChoice->count() > 1 ? portraitChoice->itemData(1).toString() : QString();
    auto root = home + "/.config/fastfetch/";
    auto color = root + "portraits/" + choice + ".png";
    auto manga = root + "manga/" + choice + ".png";
    bool available = QFile::exists(manga);
    auto art = portraitArt->currentData().toString();
    auto show = [](QLabel *label, const QString &file) {
      QImageReader reader(file);
      reader.setScaledSize(reader.size().scaled(180, 180, Qt::KeepAspectRatio));
      auto image = reader.read();
      label->setPixmap(QPixmap::fromImage(image));
      if (image.isNull()) label->setText("Portrait unavailable");
    };
    show(portraitPreview, art == "manga" && available ? manga : color);
    mangaPreview->setVisible(art == "mixed" && available);
    if (mangaPreview->isVisible()) show(mangaPreview, manga);
    auto title = choice;
    title.replace('-', ' ');
    portraitCaption->setText((sample ? "Rotation example: " : "Preview: ") + title +
        (art == "mixed" && available ? " · Color / Manga" :
         art == "manga" && available ? " · Manga" : " · Color") +
        (art != "color" && !available ? " (manga unavailable)" : "") +
        ". Previewing does not change your saved settings.");
  }
  void refreshStatus() {
    try {
      auto artwork = rpc({{"op", "portraits"}}).toObject();
      // Keep unsaved selections while polling; reload when saved preferences change.
      auto signature = QJsonDocument(artwork).toJson(QJsonDocument::Compact);
      if (portraitChoice->property("savedArtwork").toByteArray() != signature) {
        QSignalBlocker choiceBlock(portraitChoice), artBlock(portraitArt), followBlock(matchDesktop);
        portraitChoice->clear();
        portraitChoice->addItem("Random characters", "random");
        for (auto value : artwork.value("portraits").toArray()) {
          auto id = value.toString();
          auto title = id;
          title.replace('-', ' ');
          portraitChoice->addItem(title, id);
        }
        portraitChoice->setCurrentIndex(qMax(0, portraitChoice->findData(artwork.value("choice").toString())));
        portraitArt->setCurrentIndex(qMax(0, portraitArt->findData(artwork.value("art").toString())));
        matchDesktop->setChecked(artwork.value("match_desktop").toBool());
        portraitChoice->setProperty("savedArtwork", signature);
      }
      auto status = rpc({{"op", "status"}}).toObject();
      auto id = status.value("current").toString();
      savedDesktop = id;
      updatePortraitPreview();
      auto p = preset(id);
      saved->setText("SAVED PRESET\n" + p.value("title").toString() +
                     (status.value("pending").toBool()
                          ? "\nRefresh queued for login"
                          : ""));
      {
        QSignalBlocker block(autostart);
        autostart->setChecked(status.value("autostart").toBool());
      }
      auto file = data + "/current";
      if (QFile::exists(file) && !watcher.files().contains(file))
        watcher.addPath(file);
      if (tray) {
        auto description =
            "Bankai Rust · " + p.value("title").toString() +
            (status.value("pending").toBool() ? " · refresh queued" : "");
        trayStatus->setText(description);
        tray->setToolTip(description);
        if (trayPreset != id) {
          tray->setIcon(svgIcon(bootstrap.value("mask_svg").toString().toUtf8(),
                                p.value("accent").toString()));
          trayPreset = id;
        }
        for (auto it = presetActions.begin(); it != presetActions.end(); ++it) {
          it.value()->setChecked(it.key() == id);
          it.value()->setEnabled(!process);
        }
      }
    } catch (const std::exception &e) {
      notice->setText(QString::fromUtf8(e.what()));
    }
  }
  void refreshSnapshots() {
    auto previous = snapshots->currentData().toString();
    QSignalBlocker blocker(snapshots);
    snapshots->clear();
    rows.clear();
    try {
      auto values = rpc({{"op", "snapshots"}}).toArray();
      double total = 0;
      int protectedCount = 0;
      for (auto value : values) {
        auto row = value.toObject();
        auto name = row.value("name").toString();
        rows[name] = row;
        total += row.value("bytes").toDouble();
        protectedCount += row.value("protected").toBool();
        auto title = name + " · " +
                     (row.value("eligible").toBool()
                          ? sizeText(row.value("bytes").toDouble())
                          : "needs review");
        if (row.value("protected").toBool())
          title +=
              row.value("baseline").toBool() ? " · Baseline" : " · ★ Protected";
        snapshots->addItem(title, name);
      }
      storage->setText(QString("%1 snapshots · %2 stored · %3 protected")
                           .arg(values.size())
                           .arg(sizeText(total))
                           .arg(protectedCount));
      cleanupButton->setEnabled(!process);
    } catch (const std::exception &e) {
      storage->setText(QString::fromUtf8(e.what()));
      cleanupButton->setEnabled(false);
    }
    int index = snapshots->findData(previous);
    if (index >= 0)
      snapshots->setCurrentIndex(index);
    snapshotChanged();
  }
  void snapshotChanged() {
    auto row = rows.value(snapshots->currentData().toString());
    bool available = !row.isEmpty() && !process;
    verifyButton->setEnabled(available);
    restoreButton->setEnabled(available);
    protectButton->setEnabled(available && !row.value("baseline").toBool());
    protectButton->setText(row.value("protected").toBool()
                               ? "Remove protection"
                               : "Protect snapshot");
    snapshotDetails->setText(
        row.isEmpty()
            ? "No snapshots yet. Create one to save your setup."
            : QString("%1 saved files · Integrity is checked before restore.")
                  .arg(row.value("files").toInt()));
  }
  void restoreSelected() {
    auto name = snapshots->currentData().toString();
    if (name.isEmpty())
      return;
    QMessageBox dialog(QMessageBox::Warning, "Restore snapshot?",
                       "Restore desktop and terminal from " + name + "?",
                       QMessageBox::NoButton, this);
    dialog.setInformativeText(
        "Your current settings will be backed up first. Log out and back in "
        "afterward. The system login screen is managed separately.");
    auto *cancel = dialog.addButton(QMessageBox::Cancel);
    auto *restore =
        dialog.addButton("Restore snapshot", QMessageBox::AcceptRole);
    dialog.setDefaultButton(cancel);
    dialog.exec();
    if (dialog.clickedButton() == restore)
      startTask({{"op", "restore"}, {"name", name}},
                "Checking and restoring snapshot…");
  }
  void previewCleanup() {
    try {
      auto plan = rpc({{"op", "plan"}, {"keep", keep->value()}}).toObject();
      auto candidates = plan.value("candidates").toArray();
      if (candidates.isEmpty()) {
        notice->setText("No older snapshots to remove. Recent and protected "
                        "copies are kept.");
        return;
      }
      QStringList names;
      for (auto row : candidates) {
        auto item = row.toObject();
        names << item.value("name").toString() + " · " +
                     sizeText(item.value("bytes").toDouble());
      }
      QMessageBox dialog(QMessageBox::Warning, "Review cleanup",
                         QString("Permanently remove %1 older snapshots (%2)?")
                             .arg(candidates.size())
                             .arg(sizeText(plan.value("bytes").toDouble())),
                         QMessageBox::NoButton, this);
      dialog.setInformativeText(
          "Recent snapshots, the original baseline and protected copies "
          "stay.\n\n" +
          (names.size() <= 8 ? names.join("\n")
                             : "Expand details to review every snapshot."));
      dialog.setDetailedText(names.join("\n"));
      auto *cancel = dialog.addButton(QMessageBox::Cancel);
      auto *remove = dialog.addButton("Delete reviewed snapshots",
                                      QMessageBox::DestructiveRole);
      dialog.setDefaultButton(cancel);
      dialog.exec();
      if (dialog.clickedButton() == remove)
        startTask({{"op", "cleanup"}, {"plan", plan}},
                  "Removing reviewed snapshots…");
    } catch (const std::exception &e) {
      notice->setText(QString::fromUtf8(e.what()));
    }
  }
  void startTask(const QJsonObject &request, const QString &progress) {
    if (process)
      return;
    notice->setText(progress);
    portraitChoice->setEnabled(false);
    portraitArt->setEnabled(false);
    matchDesktop->setEnabled(false);
    output.clear();
    log->clear();
    for (auto *b : buttons)
      b->setEnabled(false);
    for (auto *c : cards)
      c->setEnabled(false);
    for (auto *a : taskActions)
      a->setEnabled(false);
    snapshots->setEnabled(false);
    keep->setEnabled(false);
    autostart->setEnabled(false);
    auto *worker = new QProcess(this);
    process = worker;
    worker->setProcessChannelMode(QProcess::MergedChannels);
    connect(worker, &QProcess::readyReadStandardOutput, this, [this, worker] {
      output += worker->readAllStandardOutput();
      if (output.size() > 2 * 1024 * 1024)
        output = output.right(2 * 1024 * 1024);
    });
    connect(worker, &QProcess::finished, this,
            [this, worker](int code, QProcess::ExitStatus status) {
              output += worker->readAllStandardOutput();
              auto reply = QJsonDocument::fromJson(output).object();
              bool good = code == 0 && status == QProcess::NormalExit &&
                          reply.value("ok").toBool();
              auto result = reply.value("result").toObject();
              notice->setText(
                  good ? result.value("message").toString("Action completed.")
                       : reply.value("error").toString(
                             "Action failed. See activity."));
              log->setPlainText(QString::fromUtf8(output));
              if (!good) {
                log->show();
                logButton->setText("Hide activity");
              }
              finishTask(worker);
              if (tray && tray->isVisible() && !isVisible())
                tray->showMessage("Bankai Rust", notice->text(),
                                  good ? QSystemTrayIcon::Information
                                       : QSystemTrayIcon::Warning);
            });
    connect(worker, &QProcess::errorOccurred, this,
            [this, worker](QProcess::ProcessError error) {
              if (error == QProcess::FailedToStart && process == worker) {
                notice->setText(worker->errorString());
                finishTask(worker);
              }
            });
    worker->start(QCoreApplication::applicationFilePath(), {"--rpc"});
    worker->write(QJsonDocument(request).toJson(QJsonDocument::Compact));
    worker->closeWriteChannel();
    slowTimer.start();
  }
  void finishTask(QProcess *worker) {
    if (process != worker)
      return;
    process = nullptr;
    portraitChoice->setEnabled(true);
    portraitArt->setEnabled(true);
    matchDesktop->setEnabled(true);
    slowTimer.stop();
    for (auto *b : buttons)
      b->setEnabled(true);
    for (auto *c : cards)
      c->setEnabled(true);
    for (auto *a : taskActions)
      a->setEnabled(true);
    snapshots->setEnabled(true);
    keep->setEnabled(true);
    autostart->setEnabled(true);
    refreshStatus();
    refreshSnapshots();
    worker->deleteLater();
  }
  void terminal(const QString &function = {}, const QString &title = {}) {
    QStringList args{"--class", function == "bankai-monitor"
                                    ? "bleach-monitor"
                                    : "bleach-terminal"};
    if (!title.isEmpty())
      args << "--title" << title;
    if (!function.isEmpty())
      args << "/usr/bin/fish" << "-c" << function;
    notice->setText(QProcess::startDetached("/usr/bin/kitty", args)
                        ? "Terminal opened."
                        : "Could not launch Kitty.");
  }
  void openFile(const QString &path) {
    if (!QFile::exists(path) ||
        !QDesktopServices::openUrl(QUrl::fromLocalFile(path)))
      notice->setText("Could not open " + path);
  }
  void loginSetup() {
    const QString data = QDir::homePath() + "/.local/share/bleach-desktop/";
    const QString theme = data + "login-theme";
    if (!QFile::exists(data + "install-login.py") || !QFile::exists(theme + "/Main.qml")) {
      QMessageBox::information(this, "Login screen", "Update this Bankai edition with its installer to add the manga login theme.");
      return;
    }
    QMessageBox dialog(this);
    dialog.setWindowTitle("Manga login screen");
    dialog.setText("Manga login scene follows your desktop character");
    const QString install = "sudo python3 ~/.local/share/bleach-desktop/install-login.py install";
    const QString restore = "sudo python3 ~/.local/share/bleach-desktop/install-login.py restore";
    dialog.setInformativeText("Preview without logging out. To activate or update, run:\n" + install +
        "\n\nTo restore the previous theme:\n" + restore +
        "\n\nOne-time administrator setup enables automatic matching for your account. Changes appear at the next login screen.");
    dialog.setStandardButtons(QMessageBox::Close);
    auto *preview = dialog.addButton("Preview", QMessageBox::ActionRole);
    connect(preview, &QPushButton::clicked, this, [this, theme] {
      if (QStandardPaths::findExecutable("sddm-greeter-qt6").isEmpty() ||
          !QProcess::startDetached("python3", QStringList{QDir::homePath() + "/.local/share/bleach-desktop/preview-login.py"}))
        QMessageBox::information(this, "Login preview", "Could not start sddm-greeter-qt6. Install SDDM with Qt 6 to preview this theme.");
    });
    auto *copy = dialog.addButton("Copy install command", QMessageBox::ActionRole);
    connect(copy, &QPushButton::clicked, this, [install] { qApp->clipboard()->setText(install); });
    auto *undo = dialog.addButton("Copy restore command", QMessageBox::ActionRole);
    connect(undo, &QPushButton::clicked, this, [restore] { qApp->clipboard()->setText(restore); });
    dialog.exec();
  }
  void showWindow(bool backups = false) {
    if (backups) {
      navigation->setCurrentRow(1);
      refreshSnapshots();
    }
    showNormal();
    raise();
    activateWindow();
  }
  void setupTray(bool visible = true) {
    tray = new QSystemTrayIcon(this);
    trayMenu = new QMenu(this);
    trayStatus = trayMenu->addAction("Bankai Rust");
    trayStatus->setEnabled(false);
    trayMenu->addAction("Open Bankai Rust", this, [this] { showWindow(); });
    auto *menu = trayMenu->addMenu("Switch character");
    auto *group = new QActionGroup(this);
    group->setExclusive(true);
    for (auto value : presets) {
      auto p = value.toObject();
      auto id = p.value("id").toString();
      auto *action = menu->addAction(p.value("title").toString());
      action->setCheckable(true);
      group->addAction(action);
      presetActions[id] = action;
      taskActions << action;
      connect(action, &QAction::triggered, this, [this, id] {
        if (!process) {
          selectPreset(id);
          startTask({{"op", "apply"}, {"preset", id}}, "Applying preset…");
        }
      });
    }
    trayMenu->addSeparator();
    trayMenu->addAction(
        svgIcon(bootstrap.value("terminal_svg").toString().toUtf8()),
        "Soul Society Terminal", this, [this] { terminal(); });
    trayMenu->addAction(
        svgIcon(bootstrap.value("monitor_svg").toString().toUtf8()),
        "Reiatsu Monitor", this,
        [this] { terminal("bankai-monitor", "Reiatsu Monitor"); });
    taskActions << trayMenu->addAction("Create snapshot", this, [this] {
      startTask({{"op", "backup"}}, "Creating snapshot…");
    });
    trayMenu->addAction("Backups && restore", this,
                        [this] { showWindow(true); });
    trayMenu->addSeparator();
    trayMenu->addAction("Quit Bankai Rust", this, [this] {
      if (process) {
        showWindow();
        notice->setText(
            "Wait for the current action to finish before quitting.");
        return;
      }
      quitting = true;
      tray->hide();
      qApp->quit();
    });
    tray->setContextMenu(trayMenu);
    connect(tray, &QSystemTrayIcon::activated, this,
            [this](QSystemTrayIcon::ActivationReason reason) {
              if (reason == QSystemTrayIcon::Trigger ||
                  reason == QSystemTrayIcon::DoubleClick)
                showWindow();
            });
    refreshStatus();
    if (visible)
      tray->show();
  }

protected:
  void closeEvent(QCloseEvent *event) override {
    if (process) {
      notice->setText("Let the current action finish before closing Bankai.");
      event->ignore();
    } else if (tray && tray->isVisible() && !quitting) {
      hide();
      event->ignore();
    } else
      event->accept();
  }
};
static QJsonObject benchmark(Window &window, qint64 elapsed) {
  QFile status("/proc/self/status");
  status.open(QIODevice::ReadOnly);
  QJsonObject result{{"startup_ms", double(elapsed)}, {"edition", "rust-qt"}};
  for (auto line : status.readAll().split('\n'))
    for (auto key : {QByteArray("VmRSS:"), QByteArray("VmHWM:")})
      if (line.startsWith(key))
        result.insert(QString::fromUtf8(key.chopped(1)) + "_kib",
                      QString::fromUtf8(line.mid(key.size()))
                          .simplified()
                          .split(' ')
                          .first()
                          .toDouble());
  result.insert("preset_count", window.presets.size());
  return result;
}
static int smoke(Window &window, const QString &directory) {
  auto initial = rpc({{"op", "status"}}).toObject().value("current");
  for (auto value : window.presets) {
    auto p = value.toObject();
    window.selectPreset(p.value("id").toString());
    if (window.art->image.isNull())
      throw std::runtime_error("Missing native preview wallpaper");
    auto image = svgIcon(window.bootstrap.value("mask_svg").toString().toUtf8(),
                         p.value("accent").toString())
                     .pixmap(64, 64)
                     .toImage();
    if (image.pixelColor(38, 14).name() != p.value("accent").toString())
      throw std::runtime_error("Incorrect native mask color");
  }
  if (rpc({{"op", "status"}}).toObject().value("current") != initial)
    throw std::runtime_error("Preview changed the saved preset");
  window.setupTray(false);
  if (window.presetActions.size() != 8)
    throw std::runtime_error("Missing tray actions");
  QDir().mkpath(directory);
  window.resize(1140, 820);
  window.selectPreset(initial.toString());
  window.show();
  qApp->processEvents();
  window.grab().save(directory + "/rust-appearance.png");
  auto originalArtwork = rpc({{"op", "portraits"}}).toObject();
  window.navigation->setCurrentRow(2);
  window.portraitArt->setCurrentIndex(2);
  window.matchDesktop->setChecked(!window.matchDesktop->isChecked());
  qApp->processEvents();
  if (rpc({{"op", "portraits"}}).toObject() != originalArtwork)
    throw std::runtime_error("Portrait preview changed saved settings");
  if (!window.portraitCaption->text().contains("Previewing"))
    throw std::runtime_error("Portrait preview caption missing");
  window.grab().save(directory + "/rust-terminal-art.png");
  window.navigation->setCurrentRow(1);
  qApp->processEvents();
  window.grab().save(directory + "/rust-backups.png");
  window.trayMenu->ensurePolished();
  window.trayMenu->adjustSize();
  window.trayMenu->grab().save(directory + "/rust-tray.png");
  window.resize(900, 650);
  window.navigation->setCurrentRow(0);
  qApp->processEvents();
  window.grab().save(directory + "/rust-small.png");
  auto plan = rpc({{"op", "plan"}, {"keep", 5}}).toObject();
  for (auto value : plan.value("candidates").toArray())
    if (value.toObject().value("protected").toBool())
      throw std::runtime_error("Cleanup selected a protected snapshot");
  window.startTask({{"op", "status"}}, "Checking native worker…");
  QElapsedTimer timeout;
  timeout.start();
  while (window.process && timeout.elapsed() < 5000) {
    qApp->processEvents();
    QThread::msleep(5);
  }
  if (window.process)
    throw std::runtime_error("Native worker did not finish");
  QTextStream(stdout) << "Native smoke checks passed: eight previews, mask "
                         "colors, nonmutating selection, tray actions, cleanup "
                         "protection, worker process and screenshots.\n";
  return 0;
}
extern "C" int bankai_gui(int argc, char **argv) {
  QElapsedTimer startup;
  startup.start();
  QApplication app(argc, argv);
  app.setApplicationName("Bankai Rust");
  app.setDesktopFileName("bleach-bankai-rust");
  app.setStyle("Fusion");
  auto args = app.arguments();
  bool smokeTest = args.contains("--smoke-test"),
       bench = args.contains("--benchmark");
  try {
    auto bootstrap = rpc({{"op", "bootstrap"}}).toObject();
    QString state =
        bootstrap.value("home").toString() + "/.local/state/bleach-desktop";
    QDir().mkpath(state);
    QString socketName = state + "/bankai-rust-control.sock";
    QLockFile lock(state + "/bankai-rust-control.lock");
    QLocalServer server;
    if (!smokeTest && !bench) {
      QLocalSocket client;
      client.connectToServer(socketName);
      if (client.waitForConnected(300)) {
        client.write(args.contains("tray") ? "tray\n" : (args.contains("backups") ? "backups\n" : "open\n"));
        client.waitForBytesWritten(300);
        client.disconnectFromServer();
        return 0;
      }
      if (!lock.tryLock(0)) {
        QMessageBox::information(
            nullptr, "Bankai Rust",
            "Bankai Rust is already starting. Open it from its tray icon.");
        return 0;
      }
      QLocalServer::removeServer(socketName);
      server.setSocketOptions(QLocalServer::UserAccessOption);
      if (!server.listen(socketName))
        throw std::runtime_error(server.errorString().toStdString());
    }
    Window window;
    if (bench) {
      window.show();
      app.processEvents();
      QTextStream(stdout) << QJsonDocument(benchmark(window, startup.elapsed()))
                                 .toJson(QJsonDocument::Compact)
                          << "\n";
      return 0;
    }
    if (smokeTest)
      return smoke(window,
                   qEnvironmentVariable("BANKAI_ARTIFACT_DIR",
                                        QDir::currentPath() + "/artifacts"));
    QObject::connect(&server, &QLocalServer::newConnection, &window, [&] {
      while (server.hasPendingConnections()) {
        auto *socket = server.nextPendingConnection();
        socket->setProperty("buffer", QByteArray());
        auto read = [&, socket] {
          auto bytes =
              socket->property("buffer").toByteArray() + socket->readAll();
          if (bytes.size() > 128) {
            socket->abort();
            return;
          }
          if (bytes.contains('\n')) {
            auto request = bytes.split('\n').first();
            if (request == "open" || request == "backups")
              window.showWindow(request == "backups");
            socket->disconnectFromServer();
          } else
            socket->setProperty("buffer", bytes);
        };
        QObject::connect(socket, &QLocalSocket::readyRead, &window, read);
        QObject::connect(socket, &QLocalSocket::disconnected, socket,
                         &QObject::deleteLater);
        read();
      }
    });
    bool available = QSystemTrayIcon::isSystemTrayAvailable();
    if (available || args.contains("tray")) {
      window.setupTray();
      app.setQuitOnLastWindowClosed(false);
      if (!available)
        QTimer::singleShot(10000, &window, [&] {
          if (!QSystemTrayIcon::isSystemTrayAvailable()) {
            window.tray->hide();
            app.setQuitOnLastWindowClosed(true);
            window.showMinimized();
            window.notice->setText(
                "The tray is unavailable; Bankai Rust is minimized in the taskbar.");
          }
        });
    }
    if (!args.contains("tray"))
      window.showWindow(args.contains("backups"));
    return app.exec();
  } catch (const std::exception &e) {
    if (smokeTest || bench) {
      QTextStream(stderr) << e.what() << "\n";
      return 1;
    }
    QMessageBox::critical(nullptr, "Bankai Rust", QString::fromUtf8(e.what()));
    return 1;
  }
}
