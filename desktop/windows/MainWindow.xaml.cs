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

    public MainWindow()
    {
        InitializeComponent();
        AppWindow.Resize(new global::Windows.Graphics.SizeInt32(1100, 760));
        Characters.ItemsSource = visible;
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

    private void PreviewFailed(object sender, ExceptionRoutedEventArgs args) =>
        ShowError($"Cannot decode the selected wallpaper: {args.ErrorMessage}");

    private void ShowError(string message)
    {
        Status.Title = "Bankai needs attention";
        Status.Message = message;
        Status.Severity = InfoBarSeverity.Error;
        Status.IsOpen = true;
    }
}
