using Microsoft.UI.Xaml;

namespace Bankai.Windows;

public partial class App : Application
{
    private Window? window;

    public App()
    {
        UnhandledException += (_, args) => WriteSmokeFailure(args.Exception);
        try { InitializeComponent(); }
        catch (Exception error)
        {
            WriteSmokeFailure(error);
            throw;
        }
    }

    private static void WriteSmokeFailure(Exception error)
    {
        if (Environment.GetEnvironmentVariable("BANKAI_WINDOWS_SMOKE_REPORT") is string report)
            File.WriteAllText(report, System.Text.Json.JsonSerializer.Serialize(new { success = false, error = error.ToString() }));
    }

    protected override async void OnLaunched(LaunchActivatedEventArgs args)
    {
        try
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
                finally { Exit(); }
            }
        }
        catch (Exception error)
        {
            WriteSmokeFailure(error);
            if (Environment.GetEnvironmentVariable("BANKAI_WINDOWS_SMOKE_REPORT") is not null) Exit();
            else throw;
        }
    }
}
