#include <QtNetwork>
#include <QtSvg/QSvgRenderer>
#include <QtWidgets>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <tuple>
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
static QSize minimumWindowSize(const QSize &available) {
  return QSize(qMax(1, qMin(850, available.width() - 32)),
               qMax(1, qMin(590, available.height() - 32)));
}
static QSize fitDialogSize(const QSize &requested, const QSize &available) {
  return QSize(qMax(1, qMin(requested.width(), available.width() - 32)),
               qMax(1, qMin(requested.height(), available.height() - 32)));
}
class ResponsiveDialog : public QDialog {
public:
  using QDialog::QDialog;
  std::function<void(const QSize &)> resized;

protected:
  void resizeEvent(QResizeEvent *event) override {
    QDialog::resizeEvent(event);
    if (resized)
      resized(event->size());
  }
};
static QLabel *label(const QString &text, const QString &name = {}) {
  auto *w = new QLabel(text);
  w->setWordWrap(true);
  w->setObjectName(name);
  QFont font = qApp->font();
  if (name == "brand") {
    font.setPointSizeF(font.pointSizeF() * 2.2);
    font.setLetterSpacing(QFont::AbsoluteSpacing, font.pointSizeF() * 0.25);
  } else if (name == "eyebrow") {
    font.setPointSizeF(font.pointSizeF() * 0.78);
    font.setLetterSpacing(QFont::AbsoluteSpacing, font.pointSizeF() * 0.19);
  } else if (name == "heading") {
    font.setPointSizeF(font.pointSizeF() * 1.8);
  }
  w->setFont(font);
  return w;
}
static QString accessibleText(QWidget *widget, QAccessible::Text field) {
  if (!widget)
    return {};
  const auto *interface = QAccessible::queryAccessibleInterface(widget);
  return interface ? interface->text(field) : QString();
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
  QPixmap image, scaledPreview;
  QSize previewSize;
  QJsonObject preset;
  Artwork() {
    setObjectName("appearance-artwork-preview");
    setAccessibleName("Appearance wallpaper preview");
    setMinimumHeight(200);
  }
  void select(const QJsonObject &p, const QString &wallpapers) {
    preset = p;
    setAccessibleDescription(
        QString("%1. %2. Preview of the desktop and lock screen wallpaper.")
            .arg(p.value("title").toString(), p.value("subtitle").toString()));
    QImageReader reader(wallpapers + "/" + p.value("image").toString());
    if (reader.size().isValid())
      reader.setScaledSize(reader.size().scaled(1024, 640, Qt::KeepAspectRatio));
    image = QPixmap::fromImage(reader.read());
    previewSize = QSize();
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
      if (previewSize != size()) {
        const QSize artworkSize(qRound(width() * 0.42), qRound(height() * 0.84));
        scaledPreview = image.scaled(artworkSize, Qt::KeepAspectRatio,
                                     Qt::SmoothTransformation);
        previewSize = size();
      }
      const auto &scaled = scaledPreview;
      painter.drawPixmap(width() - scaled.width(),
                         (height() - scaled.height()) / 2, scaled);
    }
    QLinearGradient gradient(0, height() * .25, 0, height());
    gradient.setColorAt(0, QColor(9, 12, 18, 0));
    gradient.setColorAt(1, QColor(9, 12, 18, 245));
    painter.fillRect(rect(), gradient);
    const QFont baseFont = qApp->font();
    const qreal fontScale = qMax(0.8, baseFont.pointSizeF() / 10.0);
    QFont eyebrowFont = baseFont;
    eyebrowFont.setPointSizeF(baseFont.pointSizeF() * 0.82);
    eyebrowFont.setLetterSpacing(QFont::AbsoluteSpacing, 2.4 * fontScale);
    QFont titleFont = baseFont;
    titleFont.setPointSizeF(baseFont.pointSizeF() * 1.85);
    titleFont.setWeight(QFont::Bold);
    QFont detailFont = baseFont;
    detailFont.setPointSizeF(baseFont.pointSizeF() * 0.82);
    const int bottom = qMax(12, qRound(baseFont.pointSizeF() * 1.2));
    const int detailBaseline = height() - bottom;
    const int titleBaseline = detailBaseline - QFontMetrics(detailFont).height() -
                              qMax(2, qRound(2 * fontScale));
    const int eyebrowBaseline = titleBaseline - QFontMetrics(titleFont).height() -
                                qMax(2, qRound(3 * fontScale));
    painter.setPen(QColor(preset.value("accent").toString()));
    painter.setFont(eyebrowFont);
    painter.drawText(24, eyebrowBaseline,
                     "SOUL SOCIETY / " +
                         preset.value("title").toString().toUpper());
    painter.setPen(Qt::white);
    painter.setFont(titleFont);
    painter.drawText(22, titleBaseline, preset.value("title").toString());
    painter.setFont(detailFont);
    painter.setPen(QColor("#bcc9da"));
    painter.drawText(24, detailBaseline, preset.value("subtitle").toString());
  }
};

class Window : public QMainWindow {
public:
  QJsonObject bootstrap;
  QJsonArray presets;
  QJsonArray customPresets;
  QString customPresetError;
  QString home, data, wallpapers, selected, trayPreset;
  QListWidget *navigation;
  QStackedWidget *pages;
  QGridLayout *presetGrid = nullptr;
  QLineEdit *presetSearch = nullptr;
  QLabel *presetEmpty = nullptr;
  int presetColumns = 4;
  Artwork *art;
  QLabel *saved, *previewNote, *storage, *snapshotDetails;
  QLabel *notice = nullptr;
  QLineEdit *snapshotSearch = nullptr;
  QComboBox *snapshots, *portraitChoice, *portraitArt;
  QStandardItemModel *snapshotModel = nullptr;
  QSortFilterProxyModel *snapshotFilter = nullptr;
  QComboBox *customPresetChoice = nullptr;
  QSpinBox *keep;
  QCheckBox *autostart, *matchDesktop;
  QPushButton *portraitChooser;
  QPushButton *inspectButton;
  QLabel *portraitPreview, *mangaPreview, *portraitCaption;
  QString savedDesktop;
  QPushButton *verifyButton, *restoreButton, *protectButton, *cleanupButton,
      *logButton;
  QPlainTextEdit *log;
  QMap<QString, QToolButton *> cards;
  QList<QPushButton *> buttons;
  QMap<QString, QJsonObject> rows;
  bool snapshotScanSucceeded = false;
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
    customPresets = bootstrap.value("custom_presets").toArray();
    customPresetError = bootstrap.value("custom_presets_error").toString();
    home = bootstrap.value("home").toString();
    data = bootstrap.value("data").toString();
    wallpapers = home + "/Pictures/Bleach-TYBW/Wallpapers";
    qApp->setStyleSheet(bootstrap.value("style").toString());
    setWindowTitle("Bankai Rust · Soul Society Control Center");
    setWindowIcon(svgIcon(bootstrap.value("mask_svg").toString().toUtf8()));
    const auto *screen = QGuiApplication::primaryScreen();
    const QSize available = screen ? screen->availableGeometry().size()
                                   : QSize(1140, 820);
    const QSize minimum = minimumWindowSize(available);
    setMinimumSize(minimum);
    resize(QSize(qMin(1140, int(available.width() * .93)),
                 qMin(820, int(available.height() * .93)))
               .expandedTo(minimum));
    auto *body = new QWidget;
    setCentralWidget(body);
    auto *layout = new QHBoxLayout(body);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(0);
    auto *sidebar = new QFrame;
    sidebar->setObjectName("sidebar");
    auto *side = new QVBoxLayout(sidebar);
    side->setContentsMargins(18, 30, 18, 23);
    side->addWidget(label("SOUL SOCIETY", "eyebrow"));
    side->addWidget(label("BANKAI", "brand"));
    side->addWidget(label("Bankai · 0.1", "muted"));
    side->addSpacing(28);
    navigation = new QListWidget;
    navigation->setAccessibleName("Main pages");
    navigation->addItems(
        {"Appearance", "Backups & restore", "Terminal & tools"});
    const int sidebarWidth =
        qMax(150, QFontMetrics(navigation->font()).horizontalAdvance("Backups & restore") + 100);
    sidebar->setMinimumWidth(sidebarWidth);
    sidebar->setMaximumWidth(qMax(240, sidebarWidth));
    navigation->item(0)->setIcon(svgIcon(bootstrap.value("mask_svg").toString().toUtf8()));
    navigation->item(1)->setIcon(svgIcon(bootstrap.value("backups_svg").toString().toUtf8()));
    navigation->item(2)->setIcon(svgIcon(bootstrap.value("terminal_svg").toString().toUtf8()));
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
        label("Choose a character to preview. Click Apply when you are ready.", "notice");
    notice->setAccessibleName("Bankai status");
    if (!customPresetError.isEmpty())
      notice->setText("Saved presets could not be loaded: " + customPresetError);
    right->addWidget(notice);
    logButton = new QPushButton("Show activity");
    logButton->setAccessibleDescription("Show or hide Bankai's action and error log.");
    logButton->setSizePolicy(QSizePolicy::Maximum, QSizePolicy::Fixed);
    right->addWidget(logButton);
    log = new QPlainTextEdit;
    log->setAccessibleName("Bankai activity log");
    log->setReadOnly(true);
    log->setMaximumHeight(110);
    log->hide();
    right->addWidget(log);
    connect(logButton, &QPushButton::clicked, this, [this] {
      log->setVisible(!log->isVisible());
      logButton->setText(log->isVisible() ? "Hide activity" : "Show activity");
    });
    layout->addWidget(content, 1);
    connect(navigation, &QListWidget::currentRowChanged, this, [this](int row) {
      pages->setCurrentIndex(row);
      if (row == 1) refreshSnapshots();
    });
    navigation->setCurrentRow(0);
    for (int row = 0; row < navigation->count(); ++row) {
      auto key = QString("Ctrl+%1").arg(row + 1);
      auto *shortcut = new QShortcut(QKeySequence(key), this);
      connect(shortcut, &QShortcut::activated, this,
              [this, row] { navigation->setCurrentRow(row); });
      navigation->item(row)->setToolTip(
          navigation->item(row)->text() + " · " + key);
    }
    slowTimer.setSingleShot(true);
    slowTimer.setInterval(120000);
    connect(&slowTimer, &QTimer::timeout, this, [this] {
      notice->setText(
          "The action is still running. See activity for progress.");
      log->show();
    });
    debounce.setSingleShot(true);
    debounce.setInterval(150);
    connect(&debounce, &QTimer::timeout, this, [this] {
      refreshStatus();
      if (customPresetChoice)
        refreshCustomPresets();
      if (pages->currentIndex() == 1)
        refreshSnapshots();
    });
    connect(&watcher, &QFileSystemWatcher::fileChanged, this,
            [this] { debounce.start(); });
    connect(&watcher, &QFileSystemWatcher::directoryChanged, this,
            [this] { debounce.start(); });
    if (QDir(data).exists())
      watcher.addPath(data);
    watchBackupDirectories();
    poll.setInterval(30000);
    connect(&poll, &QTimer::timeout, this, [this] {
      refreshStatus();
      if (pages->currentIndex() == 1)
        refreshSnapshots();
    });
    poll.start();
    refreshStatus();
    selectPreset(savedDesktop);
  }
  void resizeEvent(QResizeEvent *event) override {
    QMainWindow::resizeEvent(event);
    int columns = qBound(1, (width() - 350) / 190, 4);
    if (!presetGrid || columns == presetColumns)
      return;
    presetColumns = columns;
    layoutPresetCards();
  }
  void layoutPresetCards() {
    if (!presetGrid)
      return;
    for (auto *card : cards) presetGrid->removeWidget(card);
    int index = 0;
    for (auto value : presets) {
      const auto p = value.toObject();
      const auto id = p.value("id").toString();
      auto *card = cards.value(id);
      const auto query = presetSearch ? presetSearch->text().trimmed() : QString();
      const auto searchable = id + " " + p.value("title").toString() + " " + p.value("subtitle").toString();
      if (!query.isEmpty() && !searchable.contains(query, Qt::CaseInsensitive)) {
        card->hide();
        continue;
      }
      presetGrid->addWidget(card, index / presetColumns, index % presetColumns);
      card->show();
      ++index;
    }
    if (presetEmpty)
      presetEmpty->setVisible(index == 0);
    presetGrid->parentWidget()->layout()->activate();
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
        {
          auto value = p.toObject();
          auto options = rpc({{"op", "appearance"}}).toObject();
          if (options.value("edition").toString() == "manga") value["image"] = value["manga"];
          if (!options.value("accent").toString().isEmpty()) value["accent"] = options["accent"];
          return value;
        }
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
  void refreshCustomPresets() {
    if (!customPresetChoice) return;
    const auto previous = customPresetChoice->currentData().toString();
    try {
      customPresets = rpc({{"op", "custom-presets"}}).toArray();
      customPresetError.clear();
      if (notice && notice->text().startsWith("Saved presets could not be loaded:"))
        notice->setText("Saved presets reloaded.");
    } catch (const std::exception &e) {
      customPresetError = QString::fromUtf8(e.what());
      if (notice)
        notice->setText("Saved presets could not be loaded: " + customPresetError);
      watchCustomPresetFile();
      return;
    }
    watchCustomPresetFile();
    customPresetChoice->blockSignals(true);
    customPresetChoice->clear();
    for (auto value : customPresets) {
      auto row=value.toObject();
      customPresetChoice->addItem(row.value("name").toString(),row.value("id").toString());
    }
    const int previousIndex = customPresetChoice->findData(previous);
    if (previousIndex >= 0)
      customPresetChoice->setCurrentIndex(previousIndex);
    customPresetChoice->blockSignals(false);
    customPresetChoice->setEnabled(!customPresets.isEmpty());
  }
  void watchCustomPresetFile() {
    const auto path = data + "/custom-presets.json";
    if (QFile::exists(path) && !watcher.files().contains(path))
      watcher.addPath(path);
  }
  void saveCustomPreset() {
    bool accepted=false;
    auto name=QInputDialog::getText(this,"Save custom preset","Preset name (1–40 characters):",QLineEdit::Normal,{},&accepted);
    if(!accepted) return;
    try {
      auto options=rpc({{"op","appearance"}}).toObject();
      auto result=rpc({{"op","save-custom-preset"},{"name",name},{"preset",selected},
        {"accent",options.value("accent")},{"login",options.value("login")},{"edition",options.value("edition")}}).toObject();
      refreshCustomPresets();
      customPresetChoice->setCurrentIndex(customPresetChoice->count()-1);
      notice->setText("Saved current wallpaper, accent, and login-scene choices.");
    } catch(const std::exception &e) { QMessageBox::information(this,"Save custom preset",e.what()); }
  }
  void previewCustomPreset(int index) {
    if(index<0||index>=customPresets.size()) return;
    auto row=customPresets[index].toObject();
    selectPreset(row.value("preset").toString());
    notice->setText("Previewing saved combination ‘"+row.value("name").toString()+"’. Apply when ready.");
  }
  void applyCustomPreset() {
    auto id=customPresetChoice->currentData().toString(); if(id.isEmpty()) return;
    startTask({{"op","apply-custom-preset"},{"id",id}},"Applying saved preset…");
  }
  void deleteCustomPreset() {
    auto id=customPresetChoice->currentData().toString(); if(id.isEmpty()) return;
    try { rpc({{"op","delete-custom-preset"},{"id",id}}); refreshCustomPresets(); notice->setText("Saved preset deleted."); }
    catch(const std::exception &e) { QMessageBox::information(this,"Delete custom preset",e.what()); }
  }
  QWidget *appearancePage() {
    auto *page = new QWidget;
    auto *layout = new QVBoxLayout(page);
    layout->setSizeConstraint(QLayout::SetNoConstraint);
    page->setMinimumWidth(0);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(13);
    auto *header = new QHBoxLayout;
    header->addWidget(label("Make it yours", "heading")); header->addStretch();
    header->addWidget(button("Appearance options", [this] { appearanceOptions(); })); layout->addLayout(header);
    layout->addWidget(
        label("Matching wallpaper, lock screen and desktop colors. "
              "Eighteen characters and forms with color and manga wallpapers.",
              "muted"));
    art = new Artwork;
    layout->addWidget(art, 1);
    presetSearch = new QLineEdit;
    presetSearch->setObjectName("preset-search");
    presetSearch->setPlaceholderText("Search characters and forms…  ( / to focus )");
    presetSearch->setClearButtonEnabled(true);
    presetSearch->setAccessibleName("Search character presets");
    layout->addWidget(presetSearch);
    auto *presetSearchShortcut = new QShortcut(QKeySequence(Qt::Key_Slash), page);
    presetSearchShortcut->setObjectName("preset-search-shortcut");
    presetSearchShortcut->setContext(Qt::WidgetWithChildrenShortcut);
    connect(presetSearchShortcut, &QShortcut::activated, presetSearch, [this] {
      presetSearch->setFocus(Qt::ShortcutFocusReason);
      presetSearch->selectAll();
    });
    auto *grid = new QGridLayout;
    presetGrid = grid;
    auto *group = new QButtonGroup(this);
    group->setExclusive(true);
    int i = 0;
    for (auto item : presets) {
      auto p = item.toObject();
      auto id = p.value("id").toString();
      auto *card = new QToolButton;
      card->setCheckable(true);
      card->setObjectName("preset-card");
      card->setAccessibleName(p.value("title").toString());
      card->setAccessibleDescription(
          p.value("subtitle").toString() + ". Select to preview this character.");
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
    presetEmpty = label("No characters match that search. Try another term.", "muted");
    presetEmpty->setObjectName("preset-empty-state");
    presetEmpty->hide();
    layout->addWidget(presetEmpty);
    connect(presetSearch, &QLineEdit::textChanged, this,
            [this] { layoutPresetCards(); });
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
    auto *savedRow=new QVBoxLayout;
    customPresetChoice=new QComboBox;
    customPresetChoice->setObjectName("custom-preset-choice");
    customPresetChoice->setAccessibleName("Saved custom presets");
    customPresetChoice->setAccessibleDescription(
        "Choose a saved combination of wallpaper, accent, and login scene.");
    customPresetChoice->setMinimumWidth(190);
    connect(customPresetChoice,&QComboBox::currentIndexChanged,this,[this](int index){previewCustomPreset(index);});
    savedRow->addWidget(customPresetChoice);
    auto *savedActions = new QHBoxLayout;
    auto *saveCustom = button("Save choices",[this]{saveCustomPreset();});
    saveCustom->setObjectName("save-custom-preset");
    saveCustom->setAccessibleDescription(
        "Save the selected character with the current accent and login scene.");
    savedActions->addWidget(saveCustom);
    auto *applyCustom = button("Apply saved",[this]{applyCustomPreset();},true);
    applyCustom->setObjectName("apply-custom-preset");
    applyCustom->setAccessibleDescription(
        "Apply the selected saved character, accent, and login scene.");
    savedActions->addWidget(applyCustom);
    auto *deleteCustom = button("Delete",[this]{deleteCustomPreset();});
    deleteCustom->setObjectName("delete-custom-preset");
    deleteCustom->setAccessibleDescription("Delete the selected saved custom preset.");
    savedActions->addWidget(deleteCustom);
    savedActions->addStretch();
    savedRow->addLayout(savedActions);
    layout->addLayout(savedRow);
    refreshCustomPresets();
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
    auto *createSnapshot = button("Create snapshot", [this] {
      startTask({{"op", "backup"}}, "Creating snapshot…");
    }, true);
    createSnapshot->setIcon(svgIcon(bootstrap.value("backups_svg").toString().toUtf8()));
    layout->addWidget(createSnapshot);
    layout->addSpacing(8);
    layout->addWidget(label("SAVED SNAPSHOTS", "eyebrow"));
    snapshotSearch = new QLineEdit;
    snapshotSearch->setObjectName("snapshot-search");
    snapshotSearch->setPlaceholderText("Search saved snapshots…");
    snapshotSearch->setAccessibleName("Search saved snapshots");
    snapshotSearch->setClearButtonEnabled(true);
    layout->addWidget(snapshotSearch);
    snapshots = new QComboBox;
    snapshots->setAccessibleName("Saved snapshots");
    snapshots->setAccessibleDescription(
        "Choose a matching snapshot to inspect, verify, protect, or restore.");
    snapshotModel = new QStandardItemModel(this);
    snapshotFilter = new QSortFilterProxyModel(this);
    snapshotFilter->setSourceModel(snapshotModel);
    snapshotFilter->setFilterCaseSensitivity(Qt::CaseInsensitive);
    snapshotFilter->setFilterRole(Qt::DisplayRole);
    snapshots->setModel(snapshotFilter);
    connect(snapshotSearch, &QLineEdit::textChanged, this,
            [this](const QString &query) {
              snapshotFilter->setFilterFixedString(query.trimmed());
              snapshotChanged();
            });
    layout->addWidget(snapshots);
    snapshotDetails = label("", "muted");
    snapshotDetails->setAccessibleName("Selected snapshot details");
    auto *snapshotInfo = new QVBoxLayout;
    snapshotInfo->addWidget(snapshotDetails);
    inspectButton = button("Preview restore…", [this] {
      startTask({{"op", "inspect-snapshot"},
                 {"name", snapshots->currentData().toString()}},
                "Verifying snapshot contents…");
    });
    inspectButton->setAccessibleDescription(
        "Verify the selected snapshot and preview the files it restores or removes.");
    auto *inspectRow = new QHBoxLayout;
    inspectRow->addStretch();
    inspectRow->addWidget(inspectButton);
    snapshotInfo->addLayout(inspectRow);
    layout->addLayout(snapshotInfo);
    storage = label("", "notice");
    storage->setAccessibleName("Snapshot storage status");
    layout->addWidget(storage);
    connect(snapshots, &QComboBox::currentIndexChanged, this,
            [this] { snapshotChanged(); });
    auto *row = new QGridLayout;
    verifyButton = button("Verify", [this] {
      startTask(
          {{"op", "verify"}, {"name", snapshots->currentData().toString()}},
          "Verifying snapshot…");
    });
    row->addWidget(verifyButton, 0, 0);
    restoreButton = button("Restore…", [this] { restoreSelected(); });
    restoreButton->setAccessibleDescription(
        "Review the restore plan before changing desktop files.");
    row->addWidget(restoreButton, 0, 1);
    protectButton = button("Protect snapshot", [this] {
      auto name = snapshots->currentData().toString();
      startTask({{"op", "protect"},
                 {"name", name},
                 {"enabled", !rows[name].value("protected").toBool()}},
                "Updating protection…");
    });
    protectButton->setAccessibleDescription(
        "Keep the selected snapshot safe from automatic cleanup.");
    row->addWidget(protectButton, 1, 0);
    row->addWidget(button("Refresh", [this] { refreshSnapshots(); }), 1, 1);
    layout->addLayout(row);
    layout->addSpacing(8);
    layout->addWidget(label("CLEAN UP OLDER COPIES", "eyebrow"));
    auto *cleanup = new QVBoxLayout;
    auto *retention = new QHBoxLayout;
    retention->addWidget(label("Keep newest"));
    keep = new QSpinBox;
    keep->setRange(1, 100);
    keep->setValue(5);
    keep->setAccessibleName("Number of newest snapshots to keep");
    keep->setAccessibleDescription(
        "Protected snapshots are kept in addition to this number.");
    retention->addWidget(keep);
    retention->addWidget(label("plus all protected snapshots"));
    retention->addStretch();
    cleanup->addLayout(retention);
    auto *cleanupActions = new QHBoxLayout;
    cleanupActions->addStretch();
    cleanupButton = button("Preview cleanup…", [this] { previewCleanup(); });
    cleanupButton->setAccessibleDescription(
        "Review the exact snapshots that cleanup would remove.");
    cleanupActions->addWidget(cleanupButton);
    cleanup->addLayout(cleanupActions);
    layout->addLayout(cleanup);
    layout->addStretch();
    layout->addWidget(label("After restoring, log out and back in. The system "
                            "login screen uses its separate setup guide.",
                            "notice"));
    auto *scroll = new QScrollArea;
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    scroll->setWidget(page);
    return scroll;
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
    portraitChoice = new QComboBox(page);
    portraitChoice->setAccessibleName("Terminal character selection");
    portraitChoice->addItem("Random · shuffle current pool", "random");
    portraitChoice->hide();
    portraitChooser = button("Choose terminal character…", [this] { choosePortrait(); });
    portraitChooser->setAccessibleName("Choose terminal character");
    layout->addWidget(portraitChooser);
    matchDesktop = new QCheckBox("Match desktop character");
    matchDesktop->setAccessibleDescription(
        "Follow the character selected for the desktop; "
        "turn off to choose terminal art independently.");
    layout->addWidget(matchDesktop);
    portraitArt = new QComboBox;
    portraitArt->setAccessibleName("Portrait art style");
    portraitArt->setAccessibleDescription(
        "Choose color, manga, or both artwork styles for new terminal tabs.");
    portraitArt->addItem("Color", "color");
    portraitArt->addItem("Manga", "manga");
    portraitArt->addItem("Mixed color and manga", "mixed");
    layout->addWidget(portraitArt);
    auto *previewRow = new QHBoxLayout;
    portraitPreview = new QLabel;
    mangaPreview = new QLabel;
    portraitPreview->setObjectName("terminal-color-preview");
    portraitPreview->setAccessibleName("Terminal color artwork preview");
    mangaPreview->setObjectName("terminal-manga-preview");
    mangaPreview->setAccessibleName("Terminal manga artwork preview");
    for (auto *image : {portraitPreview, mangaPreview}) {
      image->setFixedSize(180, 180);
      image->setAlignment(Qt::AlignCenter);
      previewRow->addWidget(image);
    }
    previewRow->addStretch();
    layout->addLayout(previewRow);
    portraitCaption = label("", "muted");
    layout->addWidget(portraitCaption);
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
    autostart = new QCheckBox("Start Bankai in the tray at login");
    autostart->setAccessibleDescription(
        "Starts the Bankai Rust tray app when this user logs in. "
        "The Python edition has a separate setting.");
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
  QStringList rosterCommand(const QStringList &arguments) const {
    QProcess command;
    auto environment = QProcessEnvironment::systemEnvironment();
    environment.insert("HOME", home);
    if (qEnvironmentVariableIsSet("BANKAI_HOME") && environment.value("XDG_STATE_HOME").isEmpty())
      environment.insert("XDG_STATE_HOME", home + "/.local/state");
    command.setProcessEnvironment(environment);
    command.start(home + "/.local/bin/bankai-roster", arguments);
    if (!command.waitForStarted(1500) || !command.waitForFinished(3000) ||
        command.exitStatus() != QProcess::NormalExit || command.exitCode() != 0)
      return {};
    QStringList result;
    for (const auto &line : QString::fromUtf8(command.readAllStandardOutput()).split('\n'))
      if (!line.trimmed().isEmpty()) result << line.trimmed();
    return result;
  }
  void choosePortrait() {
    if (matchDesktop->isChecked() || process) return;
    ResponsiveDialog dialog(this);
    dialog.setObjectName("terminal-character-picker");
    dialog.setWindowTitle("Choose terminal character");
    const auto *screen = QGuiApplication::primaryScreen();
    const QSize available = screen ? screen->availableGeometry().size() : QSize(800, 700);
    dialog.resize(fitDialogSize(QSize(760, 620), available));
    auto *layout = new QVBoxLayout(&dialog);
    auto *search = new QLineEdit;
    search->setObjectName("portrait-search");
    search->setPlaceholderText("Search characters and forms…  ( / to focus )");
    search->setAccessibleName("Search terminal characters and forms");
    search->setClearButtonEnabled(true);
    layout->addWidget(search);
    auto *searchShortcut = new QShortcut(QKeySequence(Qt::Key_Slash), &dialog);
    searchShortcut->setObjectName("portrait-search-shortcut");
    searchShortcut->setContext(Qt::WidgetWithChildrenShortcut);
    connect(searchShortcut, &QShortcut::activated, search, [search] {
      search->setFocus(Qt::ShortcutFocusReason);
      search->selectAll();
    });
    auto *filters = new QComboBox;
    filters->setObjectName("portrait-filter");
    filters->setAccessibleName("Filter terminal characters");
    filters->addItem("All characters", "all");
    QMap<QString, QStringList> members;
    const auto groups = rosterCommand({"groups"});
    const QMap<QString, QString> labels = {
        {"soul-reapers", "Soul Reapers"}, {"quincy", "Quincy"},
        {"arrancars", "Arrancars"}, {"human-world", "Human world"},
        {"ichigo", "Ichigo forms"}, {"tybw-forms", "TYBW forms"},
        {"new-arrivals", "New arrivals"}};
    const QStringList groupOrder = {"soul-reapers", "quincy", "arrancars",
        "human-world", "tybw-forms", "ichigo", "new-arrivals"};
    for (const auto &group : groupOrder) {
      if (!groups.contains(group)) continue;
      filters->addItem(labels.value(group, group), group);
      members.insert(group, rosterCommand({"members", group}));
    }
    filters->addItem("Recently used", "recent");
    filters->addItem("Favorites", "favorites");
    const auto favorites = rosterCommand({"list"});
    QStringList recentlyUsed;
    QFile recentFile(home + "/.local/state/bleach/art-history.json");
    if (recentFile.open(QIODevice::ReadOnly)) {
      const auto history = QJsonDocument::fromJson(recentFile.readAll()).array();
      for (const auto &entry : history) {
        const auto id = entry.toObject().value("name").toString();
        if (!id.isEmpty() && !recentlyUsed.contains(id)) recentlyUsed << id;
      }
    }
    QMap<QString, QString> displayNames;
    for (const auto &record : rosterCommand({"catalog"})) {
      const auto fields = record.split('\t');
      if (fields.size() == 2) displayNames.insert(fields[0], fields[1]);
    }
    QString rotation = "all portraits", shuffleMode = "portrait";
    for (const auto &line : rosterCommand({"status"})) {
      if (line.startsWith("Rotation: ")) rotation = line.mid(QString("Rotation: ").size());
      else if (line.startsWith("Shuffle: ")) shuffleMode = line.mid(QString("Shuffle: ").size());
    }
    QStringList rotationPool = rotation == "favorites" ? favorites
        : rotation == "all portraits" ? displayNames.keys()
        : members.value(rotation);
    std::sort(rotationPool.begin(), rotationPool.end(), [&displayNames](const QString &left, const QString &right) {
      return displayNames.value(left, left).compare(displayNames.value(right, right), Qt::CaseInsensitive) < 0;
    });
    const int poolCount = rotationPool.size();
    const auto poolName = labels.value(rotation, rotation);
    layout->addWidget(filters);
    auto *random = new QPushButton("Random · shuffle current pool");
    random->setObjectName("primary");
    random->setAccessibleName("Choose a random terminal character");
    random->setAccessibleDescription(
        "Uses the configured terminal rotation pool and shuffle mode.");
    connect(random, &QPushButton::clicked, &dialog, [this, &dialog] {
      portraitChoice->setCurrentIndex(portraitChoice->findData("random"));
      updatePortraitPreview();
      dialog.accept();
    });
    random->setObjectName("portrait-random");
    random->setEnabled(!rotationPool.isEmpty());
    auto *randomRow = new QBoxLayout(
        dialog.width() <= 740 ? QBoxLayout::TopToBottom : QBoxLayout::LeftToRight);
    randomRow->addWidget(random, 1);
    auto *poolPreview = new QPushButton("Preview eligible characters");
    poolPreview->setObjectName("random-pool-preview");
    poolPreview->setAccessibleDescription(
        "Lists the characters currently eligible for Random selection.");
    poolPreview->setEnabled(!rotationPool.isEmpty());
    connect(poolPreview, &QPushButton::clicked, &dialog,
            [&dialog, rotationPool, poolName, shuffleMode, &displayNames] {
      QDialog preview(&dialog);
      preview.setObjectName("random-pool-dialog");
      preview.setWindowTitle("Random rotation pool");
      const auto *screen = preview.screen();
      const QSize available = screen ? screen->availableGeometry().size() : QSize(800, 700);
      preview.resize(fitDialogSize(QSize(380, 460), available));
      auto *previewLayout = new QVBoxLayout(&preview);
      previewLayout->addWidget(label(
          QString("%1 · %2 portrait%3 · %4 shuffle")
              .arg(poolName).arg(rotationPool.size())
              .arg(rotationPool.size() == 1 ? "" : "s").arg(shuffleMode), "muted"));
      auto *items = new QListWidget;
      items->setObjectName("random-pool-items");
      for (const auto &id : rotationPool) {
        auto title = displayNames.value(id, id);
        if (title == id) {
          title.replace('-', ' ');
          if (!title.isEmpty()) title[0] = title[0].toUpper();
        }
        items->addItem(title);
      }
      previewLayout->addWidget(items, 1);
      auto *close = new QDialogButtonBox(QDialogButtonBox::Close);
      connect(close, &QDialogButtonBox::rejected, &preview, &QDialog::reject);
      previewLayout->addWidget(close);
      preview.exec();
    });
    randomRow->addWidget(poolPreview);
    layout->addLayout(randomRow);
    auto *poolSummary = label(
        QString("Random uses %1 (%2 %3, %4 shuffle). Search and faction filters below only narrow direct choices.")
            .arg(poolName).arg(poolCount).arg(poolCount == 1 ? "portrait" : "portraits").arg(shuffleMode),
        "muted");
    poolSummary->setObjectName("random-pool-summary");
    layout->addWidget(poolSummary);
    auto *resultCount = label("0 characters", "muted");
    resultCount->setObjectName("portrait-results-count");
    resultCount->setAccessibleName("Matching terminal characters");
    resultCount->setAccessibleDescription(
        "0 characters shown for no search text using the All characters filter.");
    layout->addWidget(resultCount);
    auto *announcementTimer = new QTimer(&dialog);
#if QT_VERSION >= QT_VERSION_CHECK(6, 8, 0)
    announcementTimer->setObjectName("portrait-results-announcement");
    announcementTimer->setSingleShot(true);
    announcementTimer->setInterval(350);
    connect(announcementTimer, &QTimer::timeout, announcementTimer,
            [resultCount = QPointer<QLabel>(resultCount)] {
      if (!resultCount || !resultCount->isVisible() || !QAccessible::isActive())
        return;
      QAccessibleAnnouncementEvent event(resultCount, resultCount->accessibleDescription());
      event.setPoliteness(QAccessible::AnnouncementPoliteness::Polite);
      QAccessible::updateAccessibility(&event);
    });
#endif
    auto *scroll = new QScrollArea;
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    auto *gridPage = new QWidget;
    auto *grid = new QGridLayout(gridPage);
    grid->setContentsMargins(4, 4, 4, 4);
    grid->setSpacing(10);
    scroll->setWidget(gridPage);
    layout->addWidget(scroll, 1);
    auto *empty = label("No matching characters.", "muted");
    empty->setObjectName("portrait-empty-state");
    empty->hide();
    layout->addWidget(empty);
    auto *close = new QDialogButtonBox(QDialogButtonBox::Close);
    connect(close, &QDialogButtonBox::rejected, &dialog, &QDialog::reject);
    layout->addWidget(close);
    int gridAvailableWidth = dialog.width();
    QStringList previousVisibleIds;
    auto rebuild = [this, search, filters, grid, gridPage, empty, &members, &favorites,
                    &recentlyUsed, &displayNames, &dialog, &gridAvailableWidth,
                    &previousVisibleIds, announcementTimer,
                    resultCount]() {
      QString focusedId;
      for (int index = 0; index < grid->count(); ++index)
        if (auto *card = grid->itemAt(index)->widget(); card && card->hasFocus())
          focusedId = card->property("portraitId").toString();
      while (auto *item = grid->takeAt(0)) {
        if (auto *widget = item->widget()) { widget->hide(); widget->deleteLater(); }
        delete item;
      }
      const auto filter = filters->currentData().toString();
      const auto query = search->text().trimmed();
      QStringList ids;
      if (filter == "recent") {
        for (const auto &id : recentlyUsed)
          if (portraitChoice->findData(id) >= 0) ids << id;
      } else {
        for (int index = 1; index < portraitChoice->count(); ++index) {
          const auto id = portraitChoice->itemData(index).toString();
          if (filter == "all" || (filter == "favorites" && favorites.contains(id)) ||
              members.value(filter).contains(id)) ids << id;
        }
        std::sort(ids.begin(), ids.end(), [&displayNames](const QString &left, const QString &right) {
          return displayNames.value(left, left).compare(displayNames.value(right, right), Qt::CaseInsensitive) < 0;
        });
      }
      const int columnCount = qBound(1, (gridAvailableWidth - 100) / 164, 4);
      int row = 0, column = 0;
      QPushButton *restoreFocus = nullptr;
      QStringList visibleIds;
      QStringList visibleNames;
      for (const auto &id : ids) {
        auto title = displayNames.value(id, id);
        if (title == id) {
          title.replace('-', ' ');
          if (!title.isEmpty()) title[0] = title[0].toUpper();
        }
        if (!query.isEmpty() && !id.contains(query, Qt::CaseInsensitive) &&
            !title.contains(query, Qt::CaseInsensitive)) continue;
        visibleIds << id;
        visibleNames << title;
        auto *card = new QPushButton;
        card->setObjectName("portrait-card");
        card->setAccessibleName(title);
        card->setAccessibleDescription(
            QString("Choose %1 for terminal artwork. Use the arrow keys to move between cards.")
                .arg(title));
        card->setFocusPolicy(Qt::StrongFocus);
        card->setAutoDefault(false);
        card->setDefault(false);
        card->setProperty("gridRow", row);
        card->setProperty("gridColumn", column);
        card->setProperty("gridColumns", columnCount);
        card->setProperty("portraitId", id);
        card->setFixedWidth(154);
        card->setMinimumHeight(142);
        card->setStyleSheet("padding: 4px;");
        auto *cardLayout = new QVBoxLayout(card);
        cardLayout->setContentsMargins(3, 3, 3, 3);
        cardLayout->setSpacing(3);
        auto *thumbnail = new QLabel;
        thumbnail->setAlignment(Qt::AlignCenter);
        thumbnail->setFixedHeight(82);
        auto *caption = new QLabel(title);
        caption->setAlignment(Qt::AlignCenter);
        caption->setWordWrap(true);
        cardLayout->addWidget(thumbnail);
        cardLayout->addWidget(caption, 1);
        card->setMinimumHeight(qMax(142, card->minimumSizeHint().height()));
        const auto color = home + "/.config/fastfetch/portraits/" + id + ".png";
        const auto manga = home + "/.config/fastfetch/manga/" + id + ".png";
        const auto image = portraitArt->currentData().toString() == "manga" && QFile::exists(manga) ? manga : color;
        QPixmap pixmap(image);
        if (!pixmap.isNull()) thumbnail->setPixmap(pixmap.scaled(126, 82, Qt::KeepAspectRatio, Qt::SmoothTransformation));
        connect(card, &QPushButton::clicked, &dialog, [this, &dialog, id] {
          portraitChoice->setCurrentIndex(portraitChoice->findData(id));
          updatePortraitPreview();
          dialog.accept();
        });
        const auto moveFocus = [grid, card](int rowDelta, int columnDelta) {
          const int row = card->property("gridRow").toInt();
          const int column = card->property("gridColumn").toInt();
          const int rows = grid->rowCount(), columns = grid->columnCount();
          int targetRow = row + rowDelta, targetColumn = column + columnDelta;
          while (targetRow >= 0 && targetRow < rows && targetColumn >= 0 && targetColumn < columns) {
            if (auto *item = grid->itemAtPosition(targetRow, targetColumn)) {
              if (auto *target = qobject_cast<QWidget *>(item->widget())) {
                target->setFocus(Qt::TabFocusReason);
                return;
              }
            }
            targetRow += rowDelta;
            targetColumn += columnDelta;
          }
        };
        for (const auto &[key, dr, dc] : {
                 std::tuple{Qt::Key_Left, 0, -1}, std::tuple{Qt::Key_Right, 0, 1},
                 std::tuple{Qt::Key_Up, -1, 0}, std::tuple{Qt::Key_Down, 1, 0}}) {
          auto *shortcut = new QShortcut(QKeySequence(key), card);
          shortcut->setContext(Qt::WidgetShortcut);
          connect(shortcut, &QShortcut::activated, card, [moveFocus, dr, dc] { moveFocus(dr, dc); });
        }
        for (const auto key : {Qt::Key_Return, Qt::Key_Enter}) {
          auto *shortcut = new QShortcut(QKeySequence(key), card);
          shortcut->setContext(Qt::WidgetShortcut);
          connect(shortcut, &QShortcut::activated, card, [card] { card->click(); });
        }
        grid->addWidget(card, row, column++);
        if (id == focusedId)
          restoreFocus = card;
        if (column == columnCount) { column = 0; ++row; }
      }
      const bool noCards = grid->count() == 0;
      if (noCards && !query.isEmpty())
        empty->setText("No characters match that search. Try another term.");
      else if (noCards && filter == "favorites")
        empty->setText("No favorites saved yet. Add favorites in Terminal settings or choose another filter.");
      else if (noCards && filter == "recent")
        empty->setText("No recent characters yet. Open a terminal greeting, then check back here.");
      else
        empty->setText("No characters in this group. Try another filter.");
      empty->setVisible(noCards);
      const auto countText = QString("%1 character%2")
                                 .arg(grid->count())
                                 .arg(grid->count() == 1 ? "" : "s");
      const bool visibleResultsChanged = previousVisibleIds != visibleIds;
      previousVisibleIds = visibleIds;
      resultCount->setText(countText);
      const auto searchContext = query.isEmpty()
                                     ? QString("no search text")
                                     : QString("search \"%1\"").arg(query);
      QString countDescription = QString("%1 shown for %2 using the %3 filter.")
                                     .arg(countText)
                                     .arg(searchContext)
                                     .arg(filters->currentText());
      if (!visibleNames.isEmpty())
        countDescription += QString(" First result: %1.").arg(visibleNames.first());
      resultCount->setAccessibleDescription(countDescription);
#if QT_VERSION >= QT_VERSION_CHECK(6, 8, 0)
      if (visibleResultsChanged && dialog.isVisible())
        announcementTimer->start();
#else
      Q_UNUSED(announcementTimer);
      Q_UNUSED(visibleResultsChanged);
#endif
      gridPage->adjustSize();
      if (restoreFocus)
        QTimer::singleShot(0, restoreFocus,
                           [restoreFocus] { restoreFocus->setFocus(Qt::OtherFocusReason); });
    };
    connect(search, &QLineEdit::textChanged, &dialog, rebuild);
    connect(filters, &QComboBox::currentIndexChanged, &dialog, rebuild);
    rebuild();
    dialog.resized = [&dialog, randomRow, rebuild, &gridAvailableWidth](const QSize &size) {
      gridAvailableWidth = size.width();
      randomRow->setDirection(size.width() <= 740 ? QBoxLayout::TopToBottom
                                                   : QBoxLayout::LeftToRight);
      rebuild();
    };
    dialog.exec();
  }
  void updatePortraitPreview() {
    portraitChoice->setEnabled(!process && !matchDesktop->isChecked());
    portraitChooser->setEnabled(!process && !matchDesktop->isChecked());
    auto choice = portraitChoice->currentData().toString();
    if (matchDesktop->isChecked())
      choice = preset(savedDesktop).value("portrait").toString();
    bool sample = choice == "random";
    if (sample)
      choice = portraitChoice->count() > 1 ? portraitChoice->itemData(1).toString() : QString();
    const auto previewChoice = choice;
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
    auto title = previewChoice;
    title.replace('-', ' ');
    portraitCaption->setText((sample ? "Rotation example: " : "Preview: ") + title +
        (art == "mixed" && available ? " · Color / Manga" :
         art == "manga" && available ? " · Manga" : " · Color") +
        (art != "color" && !available ? " (manga unavailable)" : "") +
        ". Previewing does not change your saved settings.");
    const auto previewDescription = portraitCaption->text();
    portraitPreview->setAccessibleDescription(previewDescription);
    mangaPreview->setAccessibleDescription(previewDescription + " Manga version.");
    portraitChooser->setText("Terminal character: " +
        (sample ? QString("Random") : title));
    portraitChooser->setAccessibleDescription(
        sample ? "The current character choice is Random and uses the configured shuffle pool. "
                 "Open to choose a character or preview eligible portraits."
               : QString("The current terminal character is %1. Open to choose another character.")
                     .arg(title));
  }
  void refreshStatus() {
    try {
      auto artwork = rpc({{"op", "portraits"}}).toObject();
      // Keep unsaved selections while polling; reload when saved preferences change.
      auto signature = QJsonDocument(artwork).toJson(QJsonDocument::Compact);
      bool artworkChanged = portraitChoice->property("savedArtwork").toByteArray() != signature;
      if (artworkChanged) {
        QSignalBlocker choiceBlock(portraitChoice), artBlock(portraitArt), followBlock(matchDesktop);
        portraitChoice->clear();
        portraitChoice->addItem("Random · shuffle current pool", "random");
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
      bool desktopChanged = savedDesktop != id;
      savedDesktop = id;
      if (artworkChanged || desktopChanged)
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
  void watchBackupDirectories() {
    for (const auto &path : {home + "/Backups/Bleach-Desktop",
                             home + "/.local/state/bleach-desktop"})
      if (QDir(path).exists() && !watcher.directories().contains(path))
        watcher.addPath(path);
  }
  void snapshotScanFailed(const QString &message) {
    snapshotScanSucceeded = false;
    storage->setText(message);
    cleanupButton->setEnabled(false);
    snapshotChanged();
  }
  void refreshSnapshots() {
    watchBackupDirectories();
    auto previous = snapshots->currentData().toString();
    QJsonArray values;
    try {
      values = rpc({{"op", "snapshots"}}).toArray();
    } catch (const std::exception &e) {
      snapshotScanFailed(QString::fromUtf8(e.what()));
      return;
    }
    QSignalBlocker blocker(snapshots);
    snapshotModel->clear();
    rows.clear();
    snapshotScanSucceeded = true;
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
      auto *item = new QStandardItem(title);
      item->setData(name, Qt::UserRole);
      snapshotModel->appendRow(item);
    }
    storage->setText(QString("%1 snapshots · %2 stored · %3 protected")
                         .arg(values.size())
                         .arg(sizeText(total))
                         .arg(protectedCount));
    cleanupButton->setEnabled(!process);
    int index = snapshots->findData(previous);
    if (index >= 0)
      snapshots->setCurrentIndex(index);
    else if (snapshots->count() > 0)
      snapshots->setCurrentIndex(0);
    snapshotChanged();
  }
  void snapshotChanged() {
    auto row = rows.value(snapshots->currentData().toString());
    bool available = snapshotScanSucceeded && !row.isEmpty() && !process;
    verifyButton->setEnabled(available);
    inspectButton->setEnabled(available);
    restoreButton->setEnabled(available);
    protectButton->setEnabled(available && !row.value("baseline").toBool());
    protectButton->setText(row.value("protected").toBool()
                               ? "Remove protection"
                               : "Protect snapshot");
    if (!snapshotScanSucceeded)
      snapshotDetails->setText(
          "Snapshot refresh failed. The displayed list may be out of date; "
          "use Refresh to try again. Actions are disabled until a scan succeeds.");
    else if (row.isEmpty())
      snapshotDetails->setText(
          snapshotModel->rowCount() > 0
              ? "No matching snapshots. Clear the search to show all saved copies."
              : "No snapshots yet. Create one to save your setup.");
    else
      snapshotDetails->setText(
          QString("%1 saved files · Integrity is checked before restore.")
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
  void showSnapshotPreview(const QJsonObject &result) {
    QDialog dialog(this);
    dialog.setObjectName("snapshot-contents-dialog");
    dialog.setWindowTitle("Preview snapshot restore");
    const auto *screen = dialog.screen();
    const QSize available = screen ? screen->availableGeometry().size() : QSize(800, 700);
    dialog.resize(fitDialogSize(QSize(620, 500), available));
    auto *layout = new QVBoxLayout(&dialog);
    layout->addWidget(label(
        QString("%1 passed its integrity check. Restoring first saves your current settings.")
            .arg(result.value("name").toString()), "muted"));
    QStringList lines;
    const auto files = result.value("files").toArray();
    lines << QString("Files restored from this snapshot (%1):").arg(files.size());
    for (const auto &file : files)
      lines << file.toString();
    lines << "";
    const auto absent = result.value("absent").toArray();
    lines << QString("Settings removed because they were absent in this snapshot (%1):")
                 .arg(absent.size());
    if (absent.isEmpty())
      lines << "(none)";
    else
      for (const auto &file : absent)
        lines << file.toString();
    auto *contents = new QPlainTextEdit;
    contents->setObjectName("snapshot-restore-files");
    contents->setAccessibleName("Files changed by snapshot restore");
    contents->setReadOnly(true);
    contents->setPlainText(lines.join("\n"));
    layout->addWidget(contents, 1);
    auto *buttons = new QDialogButtonBox(QDialogButtonBox::Close);
    connect(buttons, &QDialogButtonBox::rejected, &dialog, &QDialog::reject);
    layout->addWidget(buttons);
    dialog.exec();
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
    portraitChooser->setEnabled(false);
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
            [this, worker, request](int code, QProcess::ExitStatus status) {
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
              if (good && request.value("op").toString() == "inspect-snapshot")
                showSnapshotPreview(result);
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
    portraitChooser->setEnabled(true);
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
  void appearanceOptions() {
    QJsonObject value;
    try {
      value = rpc({{"op", "appearance"}}).toObject();
    } catch (const std::exception &e) {
      const auto answer = QMessageBox::question(this, "Appearance options",
          "Saved appearance settings could not be loaded. Restore defaults and preserve a backup of this file?\n\n" +
              QString::fromUtf8(e.what()), QMessageBox::Yes | QMessageBox::No,
          QMessageBox::No);
      if (answer == QMessageBox::Yes) {
        try {
          const auto result = rpc({{"op", "repair-appearance"}}).toObject();
          notice->setText(result.value("message").toString());
        } catch (const std::exception &repairError) {
          QMessageBox::information(this, "Appearance options", QString::fromUtf8(repairError.what()));
        }
      }
      return;
    }
    QDialog dialog(this); dialog.setObjectName("appearance-options-dialog"); dialog.setWindowTitle("Appearance options");
    auto *layout = new QVBoxLayout(&dialog); auto *form = new QFormLayout;
    layout->addLayout(form);
    auto *edition = new QComboBox; edition->addItem("Color", "color"); edition->addItem("Manga", "manga");
    edition->setCurrentIndex(qMax(0, edition->findData(value.value("edition").toString())));
    form->addRow("Desktop and lock screen", edition);
    auto *accent = new QLineEdit(value.value("accent").toString()); accent->setPlaceholderText("Use character accent");
    form->addRow("Accent override (#RRGGBB)", accent);
    auto *color = new QPushButton("Choose accent color"); layout->addWidget(color);
    connect(color, &QPushButton::clicked, &dialog, [&, accent] {
      auto chosen = QColorDialog::getColor(QColor(accent->text().isEmpty() ? preset(selected).value("accent").toString() : accent->text()), &dialog);
      if (chosen.isValid()) accent->setText(chosen.name());
    });
    auto *login = new QComboBox; login->addItem("Follow background character", "follow");
    for (auto row : presets) { auto p=row.toObject(); login->addItem(p.value("title").toString()+" (fixed manga scene)",p.value("id")); }
    login->setCurrentIndex(qMax(0, login->findData(value.value("login").toString())));
    form->addRow("Login scene", login);
    auto *shuffle = new QCheckBox("Choose a different background when Bankai starts at login");
    shuffle->setChecked(value.value("shuffle_login").toBool()); layout->addWidget(shuffle);
    auto *poolHeading = new QHBoxLayout;
    poolHeading->addWidget(new QLabel("Shuffle pool (choose at least one):"));
    auto *poolCount = label("", "muted");
    poolCount->setObjectName("shuffle-pool-count");
    poolHeading->addStretch(); poolHeading->addWidget(poolCount);
    layout->addLayout(poolHeading);
    auto *poolSearch = new QLineEdit;
    poolSearch->setObjectName("shuffle-pool-search");
    poolSearch->setPlaceholderText("Filter shuffle characters…");
    poolSearch->setAccessibleName("Filter login shuffle characters");
    poolSearch->setClearButtonEnabled(true);
    layout->addWidget(poolSearch);
    auto *poolActions = new QHBoxLayout;
    auto *selectShown = new QPushButton("Select shown");
    selectShown->setObjectName("shuffle-pool-select-shown");
    selectShown->setAccessibleDescription(
        "Include every character currently visible in the filtered list.");
    auto *clearShown = new QPushButton("Clear shown");
    clearShown->setObjectName("shuffle-pool-clear-shown");
    clearShown->setAccessibleDescription(
        "Exclude every character currently visible in the filtered list.");
    poolActions->addWidget(selectShown); poolActions->addWidget(clearShown); poolActions->addStretch();
    layout->addLayout(poolActions);
    auto *pool = new QListWidget; pool->setObjectName("shuffle-pool-list"); pool->setAccessibleName("Characters for login shuffle"); pool->setAccessibleDescription("Check at least one character when login shuffle is enabled."); pool->setMaximumHeight(190); layout->addWidget(pool);
    auto *poolEmpty = label("No shuffle characters match this filter.", "muted");
    poolEmpty->setObjectName("shuffle-pool-empty-state"); poolEmpty->hide(); layout->addWidget(poolEmpty);
    for (auto row : presets) {
      auto p=row.toObject(); auto *item=new QListWidgetItem(p.value("title").toString(),pool);
      item->setData(Qt::UserRole,p.value("id")); item->setFlags(item->flags()|Qt::ItemIsUserCheckable);
      item->setCheckState(value.value("pool").toArray().contains(p.value("id")) ? Qt::Checked : Qt::Unchecked);
    }
    auto *note = new QLabel("Save options, then Apply a background for wallpaper and accent changes. Login choice syncs after one-time system setup. Enable only one Bankai edition at login for shuffle.");
    note->setWordWrap(true); layout->addWidget(note);
    auto *reset = new QPushButton("Reset to defaults");
    reset->setObjectName("reset-appearance");
    layout->addWidget(reset);
    connect(reset, &QPushButton::clicked, &dialog, [this, &dialog] {
      auto *confirm = new QMessageBox(QMessageBox::Question, "Reset appearance",
          "Restore Bankai's default appearance settings and apply the TYBW preset?",
          QMessageBox::Yes | QMessageBox::Cancel, &dialog);
      confirm->setObjectName("reset-confirmation");
      confirm->setDefaultButton(QMessageBox::Cancel);
      confirm->setAttribute(Qt::WA_DeleteOnClose);
      connect(confirm, &QMessageBox::finished, &dialog, [this, &dialog](int result) {
        if (result != QMessageBox::Yes)
          return;
        try {
          rpc({{"op", "reset-appearance"}});
          selectPreset("tybw");
          notice->setText("Appearance settings and desktop reset to Bankai defaults.");
          dialog.accept();
        } catch (const std::exception &e) {
          QMessageBox::information(&dialog, "Reset appearance", QString::fromUtf8(e.what()));
        }
      });
      confirm->open();
    });
    auto *buttons = new QDialogButtonBox(QDialogButtonBox::Save|QDialogButtonBox::Cancel); layout->addWidget(buttons);
    auto updatePoolCount = [pool, poolCount, buttons] {
      int checked = 0;
      for (int i = 0; i < pool->count(); ++i)
        if (pool->item(i)->checkState() == Qt::Checked) ++checked;
      poolCount->setText(checked == 0 ? "None selected" : QString("%1 selected").arg(checked));
      poolCount->setAccessibleDescription(poolCount->text() +
          " in the login shuffle pool.");
      buttons->button(QDialogButtonBox::Save)->setEnabled(checked > 0);
    };
    auto filterPool = [pool, poolSearch, poolEmpty] {
      const auto query = poolSearch->text().trimmed();
      int visible = 0;
      for (int i = 0; i < pool->count(); ++i) {
        auto *item = pool->item(i);
        const auto searchable = item->text() + " " + item->data(Qt::UserRole).toString();
        const bool matches = query.isEmpty() || searchable.contains(query, Qt::CaseInsensitive);
        item->setHidden(!matches);
        if (matches) ++visible;
      }
      poolEmpty->setVisible(visible == 0);
    };
    connect(poolSearch, &QLineEdit::textChanged, &dialog, filterPool);
    connect(pool, &QListWidget::itemChanged, &dialog, [updatePoolCount] { updatePoolCount(); });
    const auto setShown = [pool](Qt::CheckState state) {
      for (int i = 0; i < pool->count(); ++i)
        if (!pool->item(i)->isHidden()) pool->item(i)->setCheckState(state);
    };
    connect(selectShown, &QPushButton::clicked, &dialog, [setShown] { setShown(Qt::Checked); });
    connect(clearShown, &QPushButton::clicked, &dialog, [setShown] { setShown(Qt::Unchecked); });
    filterPool();
    updatePoolCount();
    connect(buttons,&QDialogButtonBox::rejected,&dialog,&QDialog::reject);
    connect(buttons,&QDialogButtonBox::accepted,&dialog,[&] {
      QJsonArray selectedPool; for(int i=0;i<pool->count();++i) if(pool->item(i)->checkState()==Qt::Checked) selectedPool.append(pool->item(i)->data(Qt::UserRole).toString());
      QJsonObject options{{"edition",edition->currentData().toString()},{"accent",accent->text().trimmed()},{"login",login->currentData().toString()},{"shuffle_login",shuffle->isChecked()},{"pool",selectedPool}};
      try { rpc({{"op","save-appearance"},{"appearance",options},{"expected",value}}); selectPreset(selected); notice->setText("Appearance saved. Apply a background to update wallpaper and accents."); dialog.accept(); }
      catch(const std::exception &e) {QMessageBox::information(&dialog,"Appearance options",QString::fromUtf8(e.what()));}
    });
    dialog.exec();
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
    taskActions << trayMenu->addAction(svgIcon(bootstrap.value("backups_svg").toString().toUtf8()), "Create snapshot", this, [this] {
      startTask({{"op", "backup"}}, "Creating snapshot…");
    });
    trayMenu->addAction(svgIcon(bootstrap.value("backups_svg").toString().toUtf8()), "Backups && restore", this,
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
  QJsonObject result{{"startup_ms", double(elapsed)}, {"edition", "rust-qt"}};
  if (status.open(QIODevice::ReadOnly))
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
static void smokePortraitPicker(Window &window, const QString &directory) {
  QString failure, poolPreviewFailure;
  QTimer::singleShot(150, &window, [&] {
    auto *dialog = window.findChild<QDialog *>("terminal-character-picker");
    if (!dialog) { failure = "Character picker did not open"; return; }
    auto *search = dialog->findChild<QLineEdit *>("portrait-search");
    auto *filter = dialog->findChild<QComboBox *>("portrait-filter");
    auto *cardScroll = dialog->findChild<QScrollArea *>();
    auto *resultCount = dialog->findChild<QLabel *>("portrait-results-count");
    const auto *screen = dialog->screen();
    const QSize available = screen ? screen->availableGeometry().size() : QSize(800, 700);
    if (!search || !filter || filter->findData("quincy") < 0 ||
        filter->findData("recent") < 0 || filter->findData("favorites") < 0 ||
        !cardScroll || cardScroll->horizontalScrollBar()->maximum() > 0 ||
        dialog->width() > available.width() - 32 ||
        dialog->height() > available.height() - 32 ||
        !dialog->findChild<QShortcut *>("portrait-search-shortcut") ||
        !resultCount || accessibleText(resultCount, QAccessible::Name).isEmpty() ||
        !dialog->findChild<QLabel *>("random-pool-summary") ||
        !dialog->findChild<QPushButton *>("random-pool-preview")) {
      failure = "Character picker is missing search or faction filters";
      dialog->reject();
      return;
    }
    auto *random = dialog->findChild<QPushButton *>("portrait-random");
    if (accessibleText(search, QAccessible::Name).isEmpty() ||
        accessibleText(filter, QAccessible::Name).isEmpty() ||
        !random || accessibleText(random, QAccessible::Name).isEmpty() ||
        accessibleText(window.portraitPreview, QAccessible::Name).isEmpty() ||
        accessibleText(window.portraitPreview, QAccessible::Description).isEmpty()) {
      failure = "Character selection or artwork preview is missing accessibility descriptions";
      dialog->reject();
      return;
    }
    const auto poolSummary = dialog->findChild<QLabel *>("random-pool-summary")->text();
    if (!poolSummary.contains("Random uses") || !poolSummary.contains("shuffle") ||
        !poolSummary.contains("direct choices"))
      failure = "Random picker does not explain its configured pool";
    auto *poolPreview = dialog->findChild<QPushButton *>("random-pool-preview");
    if (!poolPreview->isEnabled())
      failure = "Random pool preview is disabled despite an installed portrait";
    QTimer::singleShot(50, &window, [&] {
      auto *preview = window.findChild<QDialog *>("random-pool-dialog");
      auto *items = preview ? preview->findChild<QListWidget *>("random-pool-items") : nullptr;
      const auto *screen = preview ? preview->screen() : nullptr;
      const QSize available = screen ? screen->availableGeometry().size() : QSize(800, 700);
      bool containsUryu = false;
      if (items)
        for (int index = 0; index < items->count(); ++index)
          containsUryu = containsUryu ||
                         items->item(index)->text().contains("uryu", Qt::CaseInsensitive);
      if (!preview || preview->width() > available.width() - 32 ||
          preview->height() > available.height() - 32 || !items || items->count() < 1 ||
          !containsUryu)
        poolPreviewFailure = "Random pool preview does not show the configured eligible portrait";
      if (preview) preview->reject();
    });
    poolPreview->click();
    if (!poolPreviewFailure.isEmpty()) failure = poolPreviewFailure;
    dialog->grab().save(directory + "/rust-character-picker.png");
    filter->setCurrentIndex(filter->findData("quincy"));
    qApp->processEvents();
    search->setText("uryu");
    qApp->processEvents();
    int visible = 0;
    QPushButton *matchingCard = nullptr;
    const auto cards = dialog->findChildren<QPushButton *>("portrait-card");
    for (auto *card : cards) {
      if (card->isVisible()) {
        ++visible;
        matchingCard = card;
      }
    }
    if (visible != 1)
      failure = "Character picker search did not narrow the selected faction";
    if (!resultCount || resultCount->text() != "1 character")
      failure = "Character picker result count did not track search filters";
    if (!resultCount ||
        !accessibleText(resultCount, QAccessible::Description)
             .contains("1 character shown for search \"uryu\" using the Quincy filter. First result: Uryu."))
      failure = "Character picker accessibility description did not expose the matching count";
    if (!matchingCard || accessibleText(matchingCard, QAccessible::Name) != "Uryu" ||
        !accessibleText(matchingCard, QAccessible::Description).contains("arrow keys"))
      failure = "Character card does not explain its selection action to screen readers";
    if (cards.isEmpty() || cards.first()->findChildren<QShortcut *>().size() < 6)
      failure = "Character cards are missing keyboard navigation shortcuts";
    filter->setCurrentIndex(filter->findData("all"));
    QString replacementId;
    for (int index = 0; index < window.portraitChoice->count(); ++index) {
      const auto id = window.portraitChoice->itemData(index).toString();
      if (!id.isEmpty() && id != "random" && id != "uryu") {
        replacementId = id;
        break;
      }
    }
    search->setText(replacementId);
    qApp->processEvents();
#if QT_VERSION >= QT_VERSION_CHECK(6, 8, 0)
    auto *announcementTimer = dialog->findChild<QTimer *>("portrait-results-announcement");
    const bool announcementTimerActive = announcementTimer && announcementTimer->isActive();
#else
    const bool announcementTimerActive = false;
#endif
    QPushButton *replacementCard = nullptr;
    for (auto *card : dialog->findChildren<QPushButton *>("portrait-card"))
      if (card->isVisible()) { replacementCard = card; break; }
    if (!resultCount || resultCount->text() != "1 character" || !replacementCard ||
        replacementCard->property("portraitId").toString() != replacementId
#if QT_VERSION >= QT_VERSION_CHECK(6, 8, 0)
        || !announcementTimerActive
#endif
    )
      failure = QString("Character picker did not schedule an announcement when one result replaced another (count=%1, id=%2, timer=%3)")
                    .arg(resultCount ? resultCount->text() : "missing")
                    .arg(replacementCard ? replacementCard->property("portraitId").toString() : "missing")
                    .arg(announcementTimerActive);
    if (!resultCount ||
        !accessibleText(resultCount, QAccessible::Description)
             .contains("1 character shown for search \"test-portrait\" using the All characters filter. First result: Test Portrait."))
      failure = "Character picker did not expose the identity of its first result";
    search->setText("no-such-character");
    qApp->processEvents();
    auto *empty = dialog->findChild<QLabel *>("portrait-empty-state");
    if (!empty || !empty->isVisible() || !empty->text().contains("Try another term"))
      failure = "Character picker has no useful empty-search state";
    if (!resultCount || resultCount->text() != "0 characters")
      failure = "Character picker result count did not report empty search results";
    if (!resultCount ||
        !accessibleText(resultCount, QAccessible::Description)
             .contains("0 characters shown for search \"no-such-character\" using the All characters filter"))
      failure = "Character picker accessibility description did not expose empty results";
    if (!dialog->findChild<QPushButton *>("portrait-random"))
      failure = "Character picker is missing the random option";
    search->setText("uryu");
    qApp->processEvents();
    QPushButton *uryuCard = nullptr;
    for (auto *card : dialog->findChildren<QPushButton *>("portrait-card"))
      if (card->isVisible()) { uryuCard = card; break; }
    if (!uryuCard) {
      failure = "Character picker could not restore a matching card after an empty search";
      dialog->reject();
      return;
    }
    dialog->activateWindow();
    qApp->processEvents();
    uryuCard->setFocus(Qt::OtherFocusReason);
    qApp->processEvents();
    const bool hadCardFocus = uryuCard->hasFocus();
    const int narrowWidth = qMax(1, dialog->width() - 100);
    dialog->resize(narrowWidth, dialog->height());
    qApp->processEvents();
    if (dialog->width() > narrowWidth) {
      dialog->resize(narrowWidth, dialog->height());
      qApp->processEvents();
    }
    uryuCard = nullptr;
    for (auto *card : dialog->findChildren<QPushButton *>("portrait-card"))
      if (card->isVisible() && card->property("portraitId").toString() == "uryu") {
        uryuCard = card;
        break;
      }
    const int expectedColumns = qBound(1, (dialog->width() - 100) / 164, 4);
    if (!uryuCard) {
      failure = "Resizing the character picker lost its visible character card";
      dialog->reject();
      return;
    }
    if ((hadCardFocus && !uryuCard->hasFocus()) ||
        uryuCard->property("gridColumns").toInt() != expectedColumns ||
        cardScroll->horizontalScrollBar()->maximum() > 0)
      failure = "Resizing the character picker did not reflow cards and preserve keyboard focus";
    uryuCard->click();
    auto selectedCharacter = window.portraitChoice->currentData().toString();
    selectedCharacter.replace('-', ' ');
    if (!selectedCharacter.isEmpty())
      selectedCharacter[0] = selectedCharacter[0].toUpper();
    if (!accessibleText(window.portraitPreview, QAccessible::Description).contains(
            selectedCharacter, Qt::CaseInsensitive))
      failure = "Terminal artwork description did not update after character selection";
    dialog->reject();
  });
  window.choosePortrait();
  if (!failure.isEmpty()) throw std::runtime_error(failure.toStdString());
}
static void smokeStaleAppearanceSave(Window &window, const QJsonObject &original) {
  QString failure;
  bool messageHandled = false;
  QTimer::singleShot(100, &window, [&] {
    auto *dialog = window.findChild<QDialog *>("appearance-options-dialog");
    auto *buttons = dialog ? dialog->findChild<QDialogButtonBox *>() : nullptr;
    if (!dialog || !buttons || !buttons->button(QDialogButtonBox::Save)) {
      failure = "Appearance options Save button is missing";
      if (dialog) dialog->reject();
      messageHandled = true;
      return;
    }
    auto newer = original;
    const QString accent = original.value("accent").toString() == "#123456"
                               ? "#654321"
                               : "#123456";
    newer.insert("accent", accent);
    try {
      rpc({{"op", "save-appearance"}, {"appearance", newer}});
    } catch (const std::exception &e) {
      failure = QString("Could not stage an external appearance edit: %1").arg(e.what());
      dialog->reject();
      return;
    }
    QTimer::singleShot(50, &window, [&] {
      auto *modal = QApplication::activeModalWidget();
      auto *message = qobject_cast<QMessageBox *>(modal);
      if (!message ||
          !message->text().contains("changed in another Bankai window")) {
        failure = "Stale Appearance save did not explain the conflict";
        if (modal) modal->close();
      } else {
        message->accept();
      }
      messageHandled = true;
    });
    buttons->button(QDialogButtonBox::Save)->click();
    if (!dialog->isVisible())
      failure = "Appearance dialog closed after its stale save was rejected";
    try {
      if (rpc({{"op", "appearance"}}).toObject() != newer)
        failure = "Stale Appearance save replaced the newer shared settings";
      rpc({{"op", "save-appearance"}, {"appearance", original}});
    } catch (const std::exception &e) {
      failure = QString("Could not restore smoke appearance settings: %1").arg(e.what());
    }
    dialog->reject();
  });
  window.appearanceOptions();
  QElapsedTimer timer;
  timer.start();
  while (!messageHandled && timer.elapsed() < 250) {
    qApp->processEvents();
    QThread::msleep(5);
  }
  if (!messageHandled && failure.isEmpty())
    failure = "Stale Appearance conflict message was not handled";
  if (!failure.isEmpty())
    throw std::runtime_error(failure.toStdString());
}
static void smokeMalformedAppearanceRecovery(Window &window, const QJsonObject &original) {
  QSaveFile malformed(window.data + "/appearance.json");
  const QByteArray corruptData = "not valid json\n";
  if (!malformed.open(QIODevice::WriteOnly) ||
      malformed.write(corruptData) != corruptData.size() || !malformed.commit())
    throw std::runtime_error("Could not prepare malformed appearance settings");
  bool handled = false;
  QString failure;
  QTimer::singleShot(50, &window, [&] {
    auto *message = qobject_cast<QMessageBox *>(QApplication::activeModalWidget());
    if (!message || !message->text().contains("preserve a backup") || !message->button(QMessageBox::Yes)) {
      failure = "Malformed Appearance settings did not offer safe recovery";
      if (message) message->close();
    } else message->button(QMessageBox::Yes)->click();
    handled = true;
  });
  window.appearanceOptions();
  if (!handled)
    failure = "Malformed Appearance settings recovery prompt did not open";
  auto repaired = rpc({{"op", "appearance"}}).toObject();
  if (repaired != original)
    failure = "Malformed Appearance settings were not restored to defaults";
  const auto backups = QDir(window.data).entryList({"appearance.json.corrupt-*"}, QDir::Files);
  if (backups.size() != 1)
    failure = "Malformed Appearance settings were not backed up";
  else {
    QFile saved(window.data + "/" + backups.first());
    if (!saved.open(QIODevice::ReadOnly) || saved.readAll() != corruptData)
      failure = "Malformed Appearance backup did not preserve the original bytes";
  }
  if (!window.notice->text().contains("preserved as"))
    failure = "Appearance recovery did not show where the backup was kept";
  try {
    rpc({{"op", "save-appearance"}, {"appearance", original}});
  } catch (const std::exception &e) {
    failure = QString("Could not restore smoke appearance settings: %1").arg(e.what());
  }
  if (!failure.isEmpty())
    throw std::runtime_error(failure.toStdString());
}
static int smoke(Window &window, const QString &directory) {
  if (fitDialogSize(QSize(620, 500), QSize(640, 480)) != QSize(608, 448) ||
      fitDialogSize(QSize(380, 460), QSize(800, 600)) != QSize(380, 460))
    throw std::runtime_error("Dialog sizing does not respect available display geometry");
  const auto style = window.bootstrap.value("style").toString();
  for (const auto &selector : {"QPushButton:focus", "QToolButton:focus",
                               "QComboBox:focus", "QLineEdit:focus",
                               "QListWidget:focus", "QCheckBox:focus"})
    if (!style.contains(selector))
      throw std::runtime_error("Keyboard focus styling is missing for a control type");
  if (minimumWindowSize(QSize(800, 600)) != QSize(768, 568) ||
      minimumWindowSize(QSize(1920, 1080)) != QSize(850, 590))
    throw std::runtime_error("Window minimum size does not adapt to display geometry");
  if (!qobject_cast<QScrollArea *>(window.pages->widget(1)))
    throw std::runtime_error("Backup controls are not scrollable on short displays");
  if (accessibleText(window.snapshots, QAccessible::Name).isEmpty() ||
      accessibleText(window.snapshotSearch, QAccessible::Name).isEmpty() ||
      accessibleText(window.snapshotDetails, QAccessible::Name).isEmpty() ||
      accessibleText(window.storage, QAccessible::Name).isEmpty() ||
      accessibleText(window.navigation, QAccessible::Name).isEmpty() ||
      accessibleText(window.customPresetChoice, QAccessible::Name).isEmpty() ||
      accessibleText(window.customPresetChoice, QAccessible::Description).isEmpty() ||
      accessibleText(window.matchDesktop, QAccessible::Description).isEmpty() ||
      accessibleText(window.portraitArt, QAccessible::Description).isEmpty() ||
      accessibleText(window.portraitChooser, QAccessible::Description).isEmpty() ||
      accessibleText(window.autostart, QAccessible::Description).isEmpty() ||
      accessibleText(window.log, QAccessible::Name).isEmpty() ||
      accessibleText(window.logButton, QAccessible::Description).isEmpty() ||
      accessibleText(window.findChild<QPushButton *>("save-custom-preset"),
                     QAccessible::Description).isEmpty() ||
      accessibleText(window.findChild<QPushButton *>("apply-custom-preset"),
                     QAccessible::Description).isEmpty() ||
      accessibleText(window.findChild<QPushButton *>("delete-custom-preset"),
                     QAccessible::Description).isEmpty() ||
      accessibleText(window.inspectButton, QAccessible::Description).isEmpty() ||
      accessibleText(window.restoreButton, QAccessible::Description).isEmpty() ||
      accessibleText(window.cleanupButton, QAccessible::Description).isEmpty())
    throw std::runtime_error("Backup controls are missing screen-reader descriptions");
  if (!window.notice->text().startsWith("Saved presets could not be loaded:"))
    throw std::runtime_error("Corrupt custom presets are not surfaced in the native UI");
  if (window.snapshots->count() != 0)
    throw std::runtime_error("Smoke home unexpectedly contains saved snapshots");
  window.snapshotSearch->clear();
  const QString staleSnapshot = "smoke-stale-snapshot";
  auto *staleSnapshotItem = new QStandardItem(staleSnapshot + " · 1 KiB");
  staleSnapshotItem->setData(staleSnapshot, Qt::UserRole);
  window.snapshotModel->appendRow(staleSnapshotItem);
  window.rows.insert(staleSnapshot,
                     QJsonObject{{"name", staleSnapshot}, {"files", 2},
                                 {"eligible", true}, {"protected", false},
                                 {"baseline", false}});
  window.snapshots->setCurrentIndex(window.snapshots->findData(staleSnapshot));
  window.snapshotScanFailed("Snapshot scan failed");
  if (window.snapshots->count() != 1 ||
      window.snapshots->currentData().toString() != staleSnapshot ||
      !window.snapshotDetails->text().contains("may be out of date") ||
      window.verifyButton->isEnabled() || window.restoreButton->isEnabled() ||
      window.protectButton->isEnabled() || window.cleanupButton->isEnabled())
    throw std::runtime_error(
        "Snapshot scan failure did not preserve the stale selection safely");
  window.refreshSnapshots();
  if (!window.snapshotScanSucceeded || window.snapshots->count() != 0 ||
      !window.snapshotDetails->text().contains("No snapshots yet"))
    throw std::runtime_error("Successful empty snapshot refresh did not replace stale results");
  if (!window.watcher.files().contains(window.data + "/custom-presets.json"))
    throw std::runtime_error("Corrupt custom-preset file is not watched for recovery");
  QSaveFile repairedPresets(window.data + "/custom-presets.json");
  const QByteArray repairedData =
      R"([{"id":"custom-smoke","name":"Recovered preset","preset":"rukia","accent":"","login":"follow","edition":"color"}])";
  if (!repairedPresets.open(QIODevice::WriteOnly) ||
      repairedPresets.write(repairedData) != repairedData.size() ||
      !repairedPresets.commit())
    throw std::runtime_error("Could not prepare external custom-preset update");
  QElapsedTimer customPresetReload;
  customPresetReload.start();
  while ((window.customPresetChoice->count() != 1 ||
          window.notice->text().startsWith("Saved presets could not be loaded:")) &&
         customPresetReload.elapsed() < 1500) {
    qApp->processEvents();
    QThread::msleep(5);
  }
  if (window.customPresetChoice->count() != 1 ||
      window.customPresetChoice->itemData(0).toString() != "custom-smoke" ||
      window.notice->text() != "Saved presets reloaded.")
    throw std::runtime_error(
        QString("External custom-preset changes were not reloaded (count=%1, id=%2, notice=%3)")
            .arg(window.customPresetChoice->count())
            .arg(window.customPresetChoice->itemData(0).toString(), window.notice->text())
            .toStdString());
  auto initial = rpc({{"op", "status"}}).toObject().value("current");
  for (auto value : window.presets) {
    auto p = value.toObject();
    window.selectPreset(p.value("id").toString());
    if (window.art->image.isNull())
      throw std::runtime_error("Missing native preview wallpaper");
    if (window.art->image.width() > 1024 || window.art->image.height() > 640)
      throw std::runtime_error("Native preview exceeds its memory bound");
    auto image = svgIcon(window.bootstrap.value("mask_svg").toString().toUtf8(),
                         p.value("accent").toString())
                     .pixmap(64, 64)
                     .toImage();
    if (image.pixelColor(32, 54).name() != p.value("accent").toString())
      throw std::runtime_error("Incorrect native badge accent");
  }
  if (rpc({{"op", "status"}}).toObject().value("current") != initial)
    throw std::runtime_error("Preview changed the saved preset");
  window.setupTray(false);
  if (window.presetActions.size() != window.presets.size())
    throw std::runtime_error("Missing tray actions");
  QDir().mkpath(directory);
  window.resize(1140, 820);
  window.selectPreset(initial.toString());
  window.show();
  qApp->processEvents();
  if (window.logButton->width() < window.logButton->sizeHint().width())
    throw std::runtime_error("Activity action text is clipped at the configured font size");
  if (window.navigation->horizontalScrollBar()->maximum() > 0)
    throw std::runtime_error("Sidebar navigation labels do not fit without horizontal scrolling");
  auto *presetSearch = window.findChild<QLineEdit *>("preset-search");
  auto *presetSearchShortcut = window.findChild<QShortcut *>("preset-search-shortcut");
  if (!presetSearch || !window.findChild<QLabel *>("preset-empty-state") || !presetSearchShortcut)
    throw std::runtime_error("Appearance picker is missing search or its empty state");
  const QFont configuredFont = qApp->font();
  const QFont controlFont = presetSearch->font();
  if (controlFont.family() != configuredFont.family() ||
      controlFont.pointSizeF() != configuredFont.pointSizeF())
    throw std::runtime_error("Regular controls do not inherit the configured application font");
  auto *brandLabel = window.findChild<QLabel *>("brand");
  auto *eyebrowLabel = window.findChild<QLabel *>("eyebrow");
  auto *headingLabel = window.findChild<QLabel *>("heading");
  if (!brandLabel || !eyebrowLabel || !headingLabel ||
      qAbs(brandLabel->font().pointSizeF() / configuredFont.pointSizeF() - 2.2) > 0.1 ||
      qAbs(eyebrowLabel->font().pointSizeF() / configuredFont.pointSizeF() - 0.78) > 0.1 ||
      qAbs(headingLabel->font().pointSizeF() / configuredFont.pointSizeF() - 1.8) > 0.1)
    throw std::runtime_error("Branded and heading text does not scale with the configured font");
  auto *appearancePreview = window.art;
  auto *presetCard = window.cards.value(initial.toString());
  const auto selectedTitle = window.preset(initial.toString()).value("title").toString();
  if (accessibleText(appearancePreview, QAccessible::Name).isEmpty() ||
      !accessibleText(appearancePreview, QAccessible::Description).contains(selectedTitle) ||
      !presetCard || accessibleText(presetCard, QAccessible::Name).isEmpty() ||
      accessibleText(presetCard, QAccessible::Description).isEmpty())
    throw std::runtime_error("Appearance artwork controls are missing screen-reader descriptions");
  presetSearch->setText("quincy");
  QMetaObject::invokeMethod(presetSearchShortcut, "activated");
  qApp->processEvents();
  if (!presetSearch->hasFocus() || presetSearch->selectedText() != "quincy")
    throw std::runtime_error("Slash shortcut did not focus and select desktop preset search");
  int matchingPresets = 0;
  for (auto *card : window.findChildren<QToolButton *>("preset-card"))
    if (card->isVisible()) ++matchingPresets;
  if (matchingPresets != 1)
    throw std::runtime_error("Appearance preset search did not narrow the roster");
  presetSearch->setText("no-such-character");
  qApp->processEvents();
  auto *presetEmpty = window.findChild<QLabel *>("preset-empty-state");
  if (!presetEmpty || !presetEmpty->isVisible())
    throw std::runtime_error("Appearance picker has no useful empty-search state");
  presetSearch->clear();
  qApp->processEvents();
  window.grab().save(directory + "/rust-appearance.png");
  auto appearanceBefore = rpc({{"op", "appearance"}});
  QString poolFailure;
  QString resetCancelFailure = "Reset confirmation UI was not exercised";
  QTimer::singleShot(3000, &window, [&] {
    auto *dialog = window.findChild<QDialog *>("appearance-options-dialog");
    if (!dialog)
      dialog = qobject_cast<QDialog *>(QApplication::activeModalWidget());
    if (dialog && dialog->isVisible()) {
      resetCancelFailure = "Reset confirmation did not close in the offscreen test";
      for (auto *pending : window.findChildren<QDialog *>())
        if (pending->isVisible()) pending->reject();
    }
  });
  QTimer::singleShot(100, &window, [&] {
    auto *dialog = window.findChild<QDialog *>("appearance-options-dialog");
    if (!dialog) {
      resetCancelFailure = "Appearance options dialog did not open";
      if (auto *active = qobject_cast<QDialog *>(QApplication::activeModalWidget()))
        active->reject();
      return;
    }
    {
      auto *reset = dialog->findChild<QPushButton *>("reset-appearance");
      if (!reset) {
        resetCancelFailure = "Appearance options are missing reset to defaults";
        dialog->reject();
        return;
      }
      auto *poolSearch = dialog->findChild<QLineEdit *>("shuffle-pool-search");
      auto *pool = dialog->findChild<QListWidget *>("shuffle-pool-list");
      auto *poolCount = dialog->findChild<QLabel *>("shuffle-pool-count");
      auto *selectShown = dialog->findChild<QPushButton *>("shuffle-pool-select-shown");
      auto *clearShown = dialog->findChild<QPushButton *>("shuffle-pool-clear-shown");
      auto *poolEmpty = dialog->findChild<QLabel *>("shuffle-pool-empty-state");
      auto *optionButtons = dialog->findChild<QDialogButtonBox *>();
      if (!poolSearch || !pool || !poolCount || !selectShown || !clearShown || !poolEmpty || !optionButtons ||
          accessibleText(poolSearch, QAccessible::Name).isEmpty() ||
          accessibleText(pool, QAccessible::Name).isEmpty() ||
          accessibleText(selectShown, QAccessible::Description).isEmpty() ||
          accessibleText(clearShown, QAccessible::Description).isEmpty() ||
          accessibleText(poolCount, QAccessible::Description).isEmpty()) {
        poolFailure = "Appearance options are missing searchable shuffle-pool controls";
      } else {
        int originalSelection = 0;
        for (int i = 0; i < pool->count(); ++i)
          if (pool->item(i)->checkState() == Qt::Checked) ++originalSelection;
        poolSearch->setText("quincy");
        qApp->processEvents();
        int visible = 0;
        for (int i = 0; i < pool->count(); ++i)
          if (!pool->item(i)->isHidden()) ++visible;
        if (visible != 1)
          poolFailure = "Shuffle-pool search did not narrow to Quincy";
        bool quincyWasChecked = false;
        for (int i = 0; i < pool->count(); ++i)
          if (pool->item(i)->data(Qt::UserRole).toString() == "quincy")
            quincyWasChecked = pool->item(i)->checkState() == Qt::Checked;
        clearShown->click();
        qApp->processEvents();
        const int clearedCount = originalSelection - (quincyWasChecked ? 1 : 0);
        const auto clearedLabel = clearedCount == 0 ? QString("None selected") : QString("%1 selected").arg(clearedCount);
        if (poolCount->text() != clearedLabel)
          poolFailure = "Clear shown changed selections outside the active filter";
        selectShown->click();
        qApp->processEvents();
        if (poolCount->text() != QString("%1 selected").arg(originalSelection))
          poolFailure = "Select shown did not restore the filtered selection";
        poolSearch->clear();
        clearShown->click();
        qApp->processEvents();
        if (poolCount->text() != "None selected" || optionButtons->button(QDialogButtonBox::Save)->isEnabled())
          poolFailure = "Appearance options allow saving an empty shuffle pool";
        selectShown->click();
        qApp->processEvents();
        if (poolCount->text() != QString("%1 selected").arg(originalSelection) ||
            !optionButtons->button(QDialogButtonBox::Save)->isEnabled())
          poolFailure = "Select shown did not restore the full shuffle pool";
        poolSearch->setText("no-such-character");
        qApp->processEvents();
        if (!poolEmpty->isVisible())
          poolFailure = "Shuffle-pool filter has no empty state";
        poolSearch->clear();
        qApp->processEvents();
      }
      dialog->grab().save(directory + "/rust-appearance-options.png");
      reset->click();
      QTimer::singleShot(50, &window, [dialog, &resetCancelFailure] {
        auto *confirm = dialog->findChild<QMessageBox *>("reset-confirmation");
        if (confirm && confirm->button(QMessageBox::Cancel)) {
          confirm->button(QMessageBox::Cancel)->click();
          resetCancelFailure = "cancelled";
        } else {
          resetCancelFailure = "Reset action did not expose a cancellable confirmation";
        }
        dialog->reject();
      });
    }
  });
  window.appearanceOptions();
  if (!poolFailure.isEmpty())
    throw std::runtime_error(poolFailure.toStdString());
  if (resetCancelFailure != "cancelled")
    throw std::runtime_error(resetCancelFailure.toStdString());
  if (rpc({{"op", "appearance"}}) != appearanceBefore)
    throw std::runtime_error("Canceling appearance options changed preferences");
  smokeStaleAppearanceSave(window, appearanceBefore.toObject());
  smokeMalformedAppearanceRecovery(window, appearanceBefore.toObject());
  auto originalArtwork = rpc({{"op", "portraits"}}).toObject();
  window.navigation->setCurrentRow(2);
  window.portraitArt->setCurrentIndex(2);
  window.matchDesktop->setChecked(!window.matchDesktop->isChecked());
  qApp->processEvents();
  if (rpc({{"op", "portraits"}}).toObject() != originalArtwork)
    throw std::runtime_error("Portrait preview changed saved settings");
  if (!window.portraitCaption->text().contains("Previewing"))
    throw std::runtime_error("Portrait preview caption missing");
  window.matchDesktop->setChecked(false);
  window.portraitChoice->setCurrentIndex(window.portraitChoice->findData("random"));
  window.updatePortraitPreview();
  if (!accessibleText(window.portraitPreview, QAccessible::Description)
           .contains("Rotation example"))
    throw std::runtime_error("Random artwork preview is missing its screen-reader description");
  window.grab().save(directory + "/rust-terminal-art.png");
  window.navigation->setCurrentRow(1);
  qApp->processEvents();
  const auto snapshotDirectory = window.home + "/Backups/Bleach-Desktop";
  if (!window.watcher.directories().contains(snapshotDirectory))
    throw std::runtime_error("Backups directory is not watched for external snapshots");
  const int snapshotCount = window.snapshots->count();
  const auto wallpaperLink = window.home + "/Pictures/Bleach-TYBW/Wallpapers";
  const auto wallpaperTarget = QFileInfo(wallpaperLink).symLinkTarget();
  if (wallpaperTarget.isEmpty() || !QFile::remove(wallpaperLink))
    throw std::runtime_error("Could not isolate the snapshot smoke command from artwork links");
  QProcess externalBackup;
  externalBackup.start(QCoreApplication::applicationFilePath(), {"backup"});
  if (!externalBackup.waitForStarted(1000)) {
    QFile::link(wallpaperTarget, wallpaperLink);
    throw std::runtime_error("Could not start external snapshot smoke command");
  }
  while (externalBackup.state() != QProcess::NotRunning) {
    qApp->processEvents();
    externalBackup.waitForFinished(10);
  }
  const bool wallpaperRestored = QFile::link(wallpaperTarget, wallpaperLink);
  if (!wallpaperRestored)
    throw std::runtime_error("Could not restore the isolated artwork link after snapshot smoke");
  if (externalBackup.exitStatus() != QProcess::NormalExit || externalBackup.exitCode() != 0)
    throw std::runtime_error(
        QString("External snapshot smoke command failed (code=%1, stderr=%2)")
            .arg(externalBackup.exitCode())
            .arg(QString::fromLocal8Bit(externalBackup.readAllStandardError()))
            .toStdString());
  QElapsedTimer snapshotReload;
  snapshotReload.start();
  while (window.snapshots->count() <= snapshotCount && snapshotReload.elapsed() < 2000) {
    qApp->processEvents();
    QThread::msleep(5);
  }
  if (window.snapshots->count() <= snapshotCount)
    throw std::runtime_error("Backups page did not refresh after an external snapshot");
  const auto allSnapshots = window.snapshots->count();
  const auto searchableSnapshot = window.snapshots->currentData().toString();
  const auto searchableTitle = window.snapshots->currentText().toUpper();
  window.snapshotSearch->setText(searchableTitle);
  qApp->processEvents();
  if (window.snapshots->count() != 1 ||
      window.snapshots->currentData().toString() != searchableSnapshot)
    throw std::runtime_error("Snapshot search did not isolate a matching snapshot");
  window.snapshotSearch->setText("no-such-snapshot");
  qApp->processEvents();
  if (window.snapshots->count() != 0 || window.restoreButton->isEnabled() ||
      !window.snapshotDetails->text().contains("Clear the search"))
    throw std::runtime_error("Snapshot search did not handle empty results safely");
  window.snapshotSearch->clear();
  qApp->processEvents();
  if (window.snapshots->count() != allSnapshots)
    throw std::runtime_error("Clearing snapshot search did not restore the full list");
  QString previewFailure;
  QTimer previewTimer;
  previewTimer.setInterval(10);
  QObject::connect(&previewTimer, &QTimer::timeout, &window, [&] {
    auto *dialog = window.findChild<QDialog *>("snapshot-contents-dialog");
    if (!dialog)
      return;
    auto *contents = dialog->findChild<QPlainTextEdit *>("snapshot-restore-files");
    const auto *screen = dialog->screen();
    const QSize available = screen ? screen->availableGeometry().size() : QSize(800, 700);
    if (dialog->width() > available.width() - 32 ||
        dialog->height() > available.height() - 32 || !contents ||
        !contents->toPlainText().contains("Files restored from this snapshot (") ||
        !contents->toPlainText().contains("Settings removed because they were absent") ||
        accessibleText(contents, QAccessible::Name).isEmpty())
      previewFailure = "Restore preview is missing verified file or removal details";
    dialog->grab().save(directory + "/rust-restore-preview.png");
    dialog->accept();
    previewTimer.stop();
  });
  previewTimer.start();
  window.inspectButton->click();
  QElapsedTimer previewWait;
  previewWait.start();
  while ((window.process || previewTimer.isActive()) && previewWait.elapsed() < 5000) {
    qApp->processEvents();
    QThread::msleep(5);
  }
  if (previewTimer.isActive())
    previewFailure = "Restore preview did not open";
  if (!previewFailure.isEmpty())
    throw std::runtime_error(previewFailure.toStdString());
  window.grab().save(directory + "/rust-backups.png");
  window.trayMenu->ensurePolished();
  window.trayMenu->adjustSize();
  window.trayMenu->grab().save(directory + "/rust-tray.png");
  window.resize(900, 650);
  for (int page = 0; page < window.pages->count(); ++page) {
    window.navigation->setCurrentRow(page);
    qApp->processEvents();
    auto *scroll = qobject_cast<QScrollArea *>(window.pages->widget(page));
    if (!scroll || scroll->horizontalScrollBar()->maximum() > 0)
      throw std::runtime_error(
          QString("Control page %1 overflows horizontally at small window sizes")
              .arg(page)
              .toStdString());
    QWidget *lastControl = nullptr;
    if (page == 0)
      lastControl = window.findChild<QPushButton *>("delete-custom-preset");
    else if (page == 1)
      lastControl = window.cleanupButton;
    else
      lastControl = window.autostart;
    if (!lastControl)
      throw std::runtime_error("A control page is missing its final keyboard action");
    scroll->ensureWidgetVisible(lastControl);
    qApp->processEvents();
    const QRect controlRect(lastControl->mapTo(scroll->viewport(), QPoint(0, 0)),
                           lastControl->size());
    if (!controlRect.intersects(scroll->viewport()->rect()))
      throw std::runtime_error("A control page's final action is unreachable by scrolling");
    scroll->verticalScrollBar()->setValue(0);
  }
  window.navigation->setCurrentRow(0);
  qApp->processEvents();
  window.grab().save(directory + "/rust-small.png");
  window.navigation->setCurrentRow(2);
  window.matchDesktop->setChecked(false);
  window.updatePortraitPreview();
  smokePortraitPicker(window, directory);
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
  if (rpc({{"op", "appearance"}}) != appearanceBefore ||
      rpc({{"op", "status"}}).toObject().value("current") != initial)
    throw std::runtime_error("Offscreen UI smoke testing changed saved appearance state");
  QTextStream(stdout) << "Native smoke checks passed: all preset previews, mask "
                         "colors, nonmutating selection, tray actions, cleanup "
                         "protection, searchable preset, character and snapshot lists, "
                         "configured Random pool summary, custom-preset recovery and "
                         "external refresh, external snapshot refresh, reset confirmation, "
                         "stale appearance conflict and malformed-settings recovery, "
                         "worker process and screenshots.\n";
  return 0;
}
static bool copySmokeFile(const QString &source, const QString &destination) {
  const QFileInfo info(source);
  if (!info.exists() || info.isSymLink() || !info.isFile())
    return false;
  if (!QDir().mkpath(QFileInfo(destination).absolutePath()))
    return false;
  return QFile::copy(source, destination);
}
static bool prepareSmokeHome(const QString &source, const QString &destination) {
  const QString wallpapers = source + "/Pictures/Bleach-TYBW/Wallpapers";
  const QFileInfo wallpaperInfo(wallpapers);
  const QString smokeWallpapers = destination + "/Pictures/Bleach-TYBW/Wallpapers";
  if (!wallpaperInfo.isDir() || wallpaperInfo.isSymLink() ||
      !QDir().mkpath(QFileInfo(smokeWallpapers).absolutePath()) ||
      !QFile::link(wallpapers, smokeWallpapers))
    return false;
  if (!copySmokeFile(source + "/.local/bin/bankai-roster",
                     destination + "/.local/bin/bankai-roster") ||
      !copySmokeFile(source + "/.config/fastfetch/portraits/uryu.png",
                     destination + "/.config/fastfetch/portraits/uryu.png"))
    return false;
  QImage testPortrait(24, 24, QImage::Format_ARGB32);
  testPortrait.fill(QColor("#38bdf8"));
  if (!testPortrait.save(destination + "/.config/fastfetch/portraits/test-portrait.png"))
    return false;
  for (const auto &name : {"portrait-choice", "portrait-art-mode", "portrait-follow-desktop"}) {
    const QString path = "/.config/fastfetch/" + QString(name);
    const QString from = source + path;
    if (QFileInfo(from).exists() && !copySmokeFile(from, destination + path))
      return false;
  }
  const QString customPresets = destination + "/.local/share/bleach-desktop/custom-presets.json";
  if (!QDir().mkpath(QFileInfo(customPresets).absolutePath()))
    return false;
  QFile corruptPresets(customPresets);
  const QByteArray corruptData = "not valid json\n";
  if (!corruptPresets.open(QIODevice::WriteOnly | QIODevice::Truncate) ||
      corruptPresets.write(corruptData) != corruptData.size())
    return false;
  return QDir().mkpath(destination + "/Backups/Bleach-Desktop");
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
    std::unique_ptr<QTemporaryDir> smokeHome;
    if (smokeTest) {
      QFont configuredFont = app.font();
      configuredFont.setFamily("Sans Serif");
      configuredFont.setPointSize(17);
      app.setFont(configuredFont);
      const QString originalHome = qEnvironmentVariable("BANKAI_HOME", QDir::homePath());
      smokeHome = std::make_unique<QTemporaryDir>();
      if (!smokeHome->isValid() || !prepareSmokeHome(originalHome, smokeHome->path()))
        throw std::runtime_error("Could not prepare an isolated home for the smoke test");
      qputenv("BANKAI_HOME", smokeHome->path().toUtf8());
      qputenv("HOME", smokeHome->path().toUtf8());
      qputenv("XDG_STATE_HOME", (smokeHome->path() + "/.local/state").toUtf8());
    }
    auto bootstrap = rpc({{"op", "bootstrap"}}).toObject();
    QString state =
        bootstrap.value("home").toString() + "/.local/state/bleach-desktop";
    QString socketName = state + "/bankai-rust-control.sock";
    QLockFile lock(state + "/bankai-rust-control.lock");
    QLocalServer server;
    if (!smokeTest && !bench) {
      QDir().mkpath(state);
      if (QFileInfo(state).isSymLink() || QFileInfo(socketName).isSymLink() ||
          QFileInfo(lock.fileName()).isSymLink())
        throw std::runtime_error("Bankai state, control socket and lock paths must not be symlinks");
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
    if (args.contains("tray") && rpc({{"op", "appearance"}}).toObject().value("shuffle_login").toBool())
      window.startTask({{"op", "shuffle-login"}}, "Choosing a login background…");
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
