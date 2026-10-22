using Microsoft.UI.Xaml;

namespace Bankai.Windows;

public partial class App : Application
{
    private Window? window;

    public App() => InitializeComponent();

    protected override async void OnLaunched(LaunchActivatedEventArgs args)
    {
        var main = new MainWindow();
        window = main;
        window.Activate();
        if (Environment.GetEnvironmentVariable("BANKAI_WINDOWS_SMOKE_REPORT") is string report)
        {
            try
            {
                await main.RunSmokeCheck();
                File.WriteAllText(report, "{\"success\":true}");
            }
            catch (Exception error)
            {
                File.WriteAllText(report, System.Text.Json.JsonSerializer.Serialize(new { success = false, error = error.ToString() }));
            }
            finally { Exit(); }
        }
    }
}
