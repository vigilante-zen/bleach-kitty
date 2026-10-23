using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Automation;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;

namespace Bankai.Windows;

public sealed partial class MainWindow
{
    private TerminalPreview? terminalPreview;
    private int terminalLoadGeneration;
    private readonly List<TerminalInstallation> terminalInstallations = [];

    private void RefreshTerminalInstallations()
    {
        var selected = TerminalInstall.SelectedItem as TerminalInstallation;
        terminalInstallations.Clear();
        if (Environment.GetEnvironmentVariable("BANKAI_WINDOWS_SMOKE_REPORT") is null)
            terminalInstallations.AddRange(TerminalSettingsDocument.Discover(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData)));
        if (selected is not null && File.Exists(selected.Path) && terminalInstallations.All(item => item.Path != selected.Path))
            terminalInstallations.Add(selected);
        TerminalInstall.ItemsSource = null;
        TerminalInstall.ItemsSource = terminalInstallations;
        TerminalInstall.SelectedItem = terminalInstallations.FirstOrDefault(item => item.Path == selected?.Path)
            ?? terminalInstallations.FirstOrDefault();
        if (terminalInstallations.Count == 0)
            TerminalSettingsPath.Text = "Open Windows Terminal once, then Refresh. For a portable installation, choose its settings.json file.";
        UpdateActionControls();
    }

    private async void TerminalInstallationChanged(object sender, SelectionChangedEventArgs args)
    {
        if (!uiReady) return;
        await LoadTerminalSettings();
    }

    private async Task<bool> LoadTerminalSettings()
    {
        var generation = ++terminalLoadGeneration;
        var previousIndex = (TerminalInstall.SelectedItem as TerminalInstallation)?.Path == terminalPreview?.Path
            ? (TerminalProfiles.SelectedItem as TerminalProfile)?.Index : null;
        terminalPreview = null;
        TerminalProfiles.ItemsSource = null;
        UpdateActionControls();
        if (TerminalInstall.SelectedItem is not TerminalInstallation installation) return false;
        TerminalSettingsPath.Text = installation.Path;
        try
        {
            var preview = await Task.Run(() => new TerminalSettingsManager(stateDirectory).Load(installation.Path));
            if (generation != terminalLoadGeneration) return false;
            terminalPreview = preview;
            TerminalProfiles.ItemsSource = preview.Document.Profiles;
            TerminalProfiles.SelectedItem = preview.Document.Profiles.FirstOrDefault(item => item.Index == previousIndex)
                ?? preview.Document.Profiles.FirstOrDefault();
            UpdateActionControls();
            return true;
        }
        catch (Exception error)
        {
            if (generation == terminalLoadGeneration) ShowError($"Cannot load Terminal settings: {error.Message}");
            return false;
        }
    }

    private void RefreshTerminalClicked(object sender, RoutedEventArgs args)
    {
        if (busy) return;
        RefreshTerminalInstallations();
    }

    private async void BrowseTerminalClicked(object sender, RoutedEventArgs args)
    {
        if (busy) return;
        try
        {
            var picker = new global::Windows.Storage.Pickers.FileOpenPicker();
            picker.FileTypeFilter.Add(".json");
            picker.FileTypeFilter.Add(".jsonc");
            WinRT.Interop.InitializeWithWindow.Initialize(picker, WinRT.Interop.WindowNative.GetWindowHandle(this));
            var file = await picker.PickSingleFileAsync();
            if (file is null) return;
            var installation = terminalInstallations.FirstOrDefault(item => item.Path == file.Path)
                ?? new TerminalInstallation("Selected settings file", file.Path);
            if (!terminalInstallations.Contains(installation)) terminalInstallations.Add(installation);
            TerminalInstall.ItemsSource = null;
            TerminalInstall.ItemsSource = terminalInstallations;
            TerminalInstall.SelectedItem = installation;
        }
        catch (Exception error) { ShowError($"Cannot choose Terminal settings: {error.Message}"); }
    }

    private void TerminalProfileChanged(object sender, SelectionChangedEventArgs args)
    {
        if (uiReady) UpdateActionControls();
    }

    private void TerminalCharacterChanged(object sender, SelectionChangedEventArgs args)
    {
        if (!uiReady || TerminalCharacter.SelectedItem is not Preset preset) return;
        var scheme = TerminalScheme.ForPreset(preset);
        TerminalSample.Background = ColorBrush(scheme.Colors["background"]);
        TerminalPrompt.Foreground = ColorBrush(scheme.Colors["cursorColor"]);
        TerminalOutput.Foreground = ColorBrush(scheme.Colors["foreground"]);
        TerminalSwatches.Children.Clear();
        foreach (var (name, color) in scheme.Colors.Where(pair => pair.Key is not ("background" or "foreground" or "cursorColor" or "selectionBackground")))
        {
            var swatch = new Border { Width = 18, Height = 18, CornerRadius = new CornerRadius(3), Background = ColorBrush(color) };
            AutomationProperties.SetName(swatch, $"{name}: {color}");
            ToolTipService.SetToolTip(swatch, $"{name}: {color}");
            TerminalSwatches.Children.Add(swatch);
        }
        AutomationProperties.SetHelpText(TerminalSample, $"{scheme.Name}. Background {scheme.Colors["background"]}, text {scheme.Colors["foreground"]}, cursor and selection {scheme.Colors["cursorColor"]}.");
        UpdateActionControls();
    }

    private static SolidColorBrush ColorBrush(string hex) => new(global::Windows.UI.Color.FromArgb(255,
        Convert.ToByte(hex.Substring(1, 2), 16), Convert.ToByte(hex.Substring(3, 2), 16), Convert.ToByte(hex.Substring(5, 2), 16)));

    private void UpdateActionControls()
    {
        if (!uiReady) return;
        Search.IsEnabled = Characters.IsEnabled = !busy;
        ApplyWallpaper.IsEnabled = previewReady && !busy;
        RestoreWallpaper.IsEnabled = !busy && File.Exists(Path.Combine(stateDirectory, "previous-wallpaper.json"));
        TerminalInstall.IsEnabled = TerminalProfiles.IsEnabled = TerminalCharacter.IsEnabled = BrowseTerminal.IsEnabled = RefreshTerminal.IsEnabled = !busy;
        ApplyTerminal.IsEnabled = !busy && terminalPreview is not null && TerminalProfiles.SelectedItem is TerminalProfile && TerminalCharacter.SelectedItem is Preset;
        RestoreTerminal.IsEnabled = !busy && terminalPreview is not null && new TerminalSettingsManager(stateDirectory).CanRestore(terminalPreview.Path);
    }

    private async void ApplyTerminalClicked(object sender, RoutedEventArgs args) => await UpdateTerminal(restore: false);
    private async void RestoreTerminalClicked(object sender, RoutedEventArgs args) => await UpdateTerminal(restore: true);

    private async Task UpdateTerminal(bool restore)
    {
        if (busy || terminalPreview is not { } preview) return;
        var profile = TerminalProfiles.SelectedItem as TerminalProfile;
        var preset = TerminalCharacter.SelectedItem as Preset;
        if (!restore && (profile is null || preset is null)) return;
        busy = true;
        UpdateActionControls();
        ShowStatus("Updating Terminal", "Saving recovery data and updating your settings…");
        try
        {
            var scheme = restore ? null : TerminalScheme.ForPreset(preset!);
            await Task.Run(() =>
            {
                var manager = new TerminalSettingsManager(stateDirectory);
                if (restore) manager.Restore(preview);
                else manager.Apply(preview, profile!, scheme!);
            });
            if (await LoadTerminalSettings())
                ShowStatus("Terminal updated", restore
                    ? "Previous Terminal settings restored. The settings they replaced were also saved."
                    : $"{scheme!.Name} applied to {profile!.Label}. Terminal normally reloads settings automatically; reopen a tab if needed.", InfoBarSeverity.Success);
        }
        catch (Exception error) { ShowError(error.Message); }
        finally { busy = false; UpdateActionControls(); }
    }

    private async Task RunTerminalSmokeCheck()
    {
        Pages.SelectedItem = TerminalTab;
        Directory.CreateDirectory(stateDirectory);
        var path = Path.Combine(stateDirectory, "fixture-settings.json");
        var original = System.Text.Encoding.UTF8.GetBytes("{ // keep this comment\n\"profiles\":{\"defaults\":{},\"list\":[{\"name\":\"PowerShell\",\"font\":{\"size\":14}}]},\"schemes\":[],\"actions\":[]}");
        File.WriteAllBytes(path, original);
        var fixture = new TerminalInstallation("Isolated test settings", path);
        terminalInstallations.Add(fixture);
        TerminalInstall.ItemsSource = null;
        TerminalInstall.ItemsSource = terminalInstallations;
        TerminalInstall.SelectedItem = fixture;
        await WaitFor(() => terminalPreview?.Path == path && TerminalProfiles.Items.Count == 2,
            "Terminal settings and profile controls did not load.");
        TerminalProfiles.SelectedIndex = 1;
        TerminalCharacter.SelectedItem = presets.First(p => p.Id == "rukia");
        await WaitFor(() => ApplyTerminal.IsEnabled && TerminalSwatches.Children.Count == 16 &&
            AutomationProperties.GetHelpText(TerminalSample).Contains("Bankai Rukia"),
            "Terminal color preview or Apply control did not become available.");
        if (!File.ReadAllBytes(path).AsSpan().SequenceEqual(original))
            throw new InvalidOperationException("Terminal preview modified settings before Apply.");
        await UpdateTerminal(restore: false);
        var applied = File.ReadAllText(path);
        if (!applied.Contains("Bankai Rukia") || !applied.Contains("keep this comment") || !RestoreTerminal.IsEnabled)
            throw new InvalidOperationException("Terminal Apply failed to preserve comments or enable recovery.");
        await UpdateTerminal(restore: true);
        if (!File.ReadAllBytes(path).AsSpan().SequenceEqual(original))
            throw new InvalidOperationException("Terminal Restore did not recover the exact original settings.");
        Directory.Delete(stateDirectory, recursive: true);
    }
}
