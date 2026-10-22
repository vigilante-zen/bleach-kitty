using System.Collections.ObjectModel;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Automation;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media.Imaging;

namespace Bankai.Windows;

public sealed partial class MainWindow : Window
{
    private IReadOnlyList<Preset> presets = Array.Empty<Preset>();
    private readonly ObservableCollection<Preset> visible = new();
    private readonly string stateDirectory = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Bankai");
    private bool busy;
    private bool previewReady;

    public MainWindow()
    {
        InitializeComponent();
        AppWindow.Resize(new global::Windows.Graphics.SizeInt32(1100, 760));
        Characters.ItemsSource = visible;
        RestoreWallpaper.IsEnabled = File.Exists(Path.Combine(stateDirectory, "previous-wallpaper.json"));
        AppWindow.Closing += (_, args) =>
        {
            if (busy) args.Cancel = true;
        };
        try
        {
            presets = PresetCatalog.Load();
            Filter();
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException or System.Text.Json.JsonException or KeyNotFoundException or InvalidOperationException)
        {
            ShowError($"Could not load the character catalog: {error.Message}");
        }
    }

    private void SearchChanged(object sender, TextChangedEventArgs args) => Filter();

    private void Filter()
    {
        if (Characters is null) return;
        var selectedId = (Characters.SelectedItem as Preset)?.Id;
        var query = Search.Text.Trim();
        visible.Clear();
        foreach (var preset in presets.Where(p =>
            p.Title.Contains(query, StringComparison.OrdinalIgnoreCase) ||
            p.Subtitle.Contains(query, StringComparison.OrdinalIgnoreCase)))
            visible.Add(preset);
        Characters.SelectedItem = visible.FirstOrDefault(p => p.Id == selectedId) ?? visible.FirstOrDefault();
        AutomationProperties.SetHelpText(Characters, $"{visible.Count} matching characters.");
    }

    private void SelectionChanged(object sender, SelectionChangedEventArgs args)
    {
        previewReady = false;
        ApplyWallpaper.IsEnabled = false;
        Preview.Source = null;
        if (Characters.SelectedItem is not Preset preset)
        {
            CharacterTitle.Text = "No matching characters";
            CharacterDescription.Text = "Try a different search.";
            AutomationProperties.SetName(Preview, "No wallpaper selected");
            return;
        }

        CharacterTitle.Text = preset.Title;
        CharacterDescription.Text = preset.Subtitle;
        AutomationProperties.SetName(Preview, $"{preset.Title} wallpaper preview");
        try
        {
            var path = PresetCatalog.WallpaperPath(preset);
            if (!File.Exists(path)) throw new FileNotFoundException("Wallpaper asset is missing.", path);
            Preview.Source = new BitmapImage { DecodePixelWidth = 1600, UriSource = new Uri(path) };
        }
        catch (Exception error) when (error is IOException or ArgumentException)
        {
            ShowError($"Cannot preview {preset.Title}: {error.Message}");
        }
    }

    private void PreviewOpened(object sender, RoutedEventArgs args)
    {
        previewReady = Characters.SelectedItem is Preset;
        ApplyWallpaper.IsEnabled = previewReady && !busy;
        ShowStatus("Windows edition preview", "Apply changes the wallpaper on all monitors. The previous background is backed up first.");
    }

    private void PreviewFailed(object sender, ExceptionRoutedEventArgs args)
    {
        previewReady = false;
        ApplyWallpaper.IsEnabled = false;
        ShowError($"Cannot decode the selected wallpaper: {args.ErrorMessage}");
    }

    private async void ApplyClicked(object sender, RoutedEventArgs args)
    {
        if (busy || !previewReady || Characters.SelectedItem is not Preset preset) return;
        await RunWallpaperAction(manager => manager.Apply(PresetCatalog.WallpaperPath(preset)),
            $"{preset.Title} wallpaper applied. Your previous background can be restored.");
    }

    private async void RestoreClicked(object sender, RoutedEventArgs args)
    {
        if (busy) return;
        await RunWallpaperAction(manager => manager.RestorePrevious(),
            "Previous wallpaper restored. The background you replaced has also been saved.");
    }

    private async Task RunWallpaperAction(Action<WallpaperManager> action, string success)
    {
        busy = true;
        ApplyWallpaper.IsEnabled = RestoreWallpaper.IsEnabled = Search.IsEnabled = Characters.IsEnabled = false;
        ShowStatus("Updating your background", "Saving recovery data and updating Windows. Please wait before closing Bankai.");
        try
        {
            var completion = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
            var worker = new Thread(() =>
            {
                try
                {
                    using var backend = new WindowsWallpaperBackend();
                    action(new WallpaperManager(stateDirectory, backend));
                    completion.SetResult();
                }
                catch (Exception error) { completion.SetException(error); }
            });
            worker.SetApartmentState(ApartmentState.STA);
            worker.Start();
            await completion.Task;
            ShowStatus("Background updated", success, InfoBarSeverity.Success);
        }
        catch (Exception error) { ShowError(error.Message); }
        finally
        {
            busy = false;
            Search.IsEnabled = Characters.IsEnabled = true;
            ApplyWallpaper.IsEnabled = previewReady;
            RestoreWallpaper.IsEnabled = File.Exists(Path.Combine(stateDirectory, "previous-wallpaper.json"));
        }
    }

    internal async Task RunSmokeCheck()
    {
        var deadline = DateTime.UtcNow.AddSeconds(20);
        while (!previewReady && DateTime.UtcNow < deadline) await Task.Delay(100);
        if (!previewReady || visible.Count != presets.Count || presets.Count == 0)
            throw new InvalidOperationException("Initial catalog or wallpaper preview did not load.");
        Search.Text = "rukia";
        if (visible.Count != 1 || (Characters.SelectedItem as Preset)?.Id != "rukia")
            throw new InvalidOperationException("Character filtering failed.");
        Search.Text = "no-matching-character-fixture";
        if (visible.Count != 0 || ApplyWallpaper.IsEnabled || Preview.Source is not null)
            throw new InvalidOperationException("Empty search retained an actionable wallpaper.");
        Search.Text = "";
        if (visible.Count != presets.Count) throw new InvalidOperationException("Clearing search did not restore the catalog.");
    }

    private void ShowStatus(string title, string message, InfoBarSeverity severity = InfoBarSeverity.Informational)
    {
        Status.Title = title;
        Status.Message = message;
        Status.Severity = severity;
        Status.IsOpen = true;
    }

    private void ShowError(string message)
    {
        Status.Title = "Bankai needs attention";
        Status.Message = message;
        Status.Severity = InfoBarSeverity.Error;
        Status.IsOpen = true;
    }
}
