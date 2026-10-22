using System.Text.Json;
using Bankai.Windows;

var checks = new (string Name, Action<Fixture> Run)[]
{
    ("Apply preserves images, monitor IDs, layout and background color", f =>
    {
        f.Manager.Apply(f.NewImage);
        var saved = f.Saved();
        Require(saved.Position == 3 && saved.BackgroundColor == 123, "Desktop options were not saved.");
        Require(saved.Monitors.Length == 2 && saved.Monitors[1].Image == "", "Solid-color monitor was not preserved.");
        Require(saved.Monitors[0].MonitorId == "monitor-a", "Monitor ID changed.");
        File.Delete(f.OldImage);
        Require(File.ReadAllText(saved.Monitors[0].Image) == "old image", "Backup depended on the original image.");
        Require(f.Backend.Current.Monitors.All(m => File.ReadAllText(m.Image) == "new image"), "New wallpaper was not installed.");
    }),
    ("Restore works after reopening and saves the background it replaces", f =>
    {
        f.Manager.Apply(f.NewImage);
        File.Delete(f.NewImage);
        new WallpaperManager(f.State, f.Backend).RestorePrevious();
        Require(File.ReadAllText(f.Backend.Current.Monitors[0].Image) == "old image", "Restore did not use the backup.");
        Require(f.Backend.Current.Monitors[1].Image == "", "Solid-color monitor was not restored.");
        f.Manager.RestorePrevious();
        Require(File.ReadAllText(f.Backend.Current.Monitors[0].Image) == "new image", "Restore could not be undone.");
    }),
    ("Failed apply rolls back a partially changed desktop", f =>
    {
        f.Backend.FailApply = true;
        Throws<IOException>(() => f.Manager.Apply(f.NewImage));
        Require(f.Backend.RestoreCalls == 1, "Recovery was not attempted.");
        Require(File.ReadAllText(f.Backend.Current.Monitors[0].Image) == "old image", "Recovery failed.");
        Require(f.Manager.CanRestore, "Recovery metadata was not saved.");
    }),
    ("Recovery failure is reported with both errors", f =>
    {
        f.Backend.FailApply = f.Backend.FailRestore = true;
        var error = Throws<AggregateException>(() => f.Manager.Apply(f.NewImage));
        Require(error.InnerExceptions.Count == 2 && f.Manager.CanRestore, "Failure lost recovery information.");
    }),
    ("Missing selected artwork causes no desktop writes", f =>
    {
        Throws<FileNotFoundException>(() => f.Manager.Apply(Path.Combine(f.Root, "missing.png")));
        Require(f.Backend.ApplyCalls == 0 && f.Backend.RestoreCalls == 0, "Missing artwork changed the desktop.");
    }),
    ("Failed backup publication prevents desktop changes", f =>
    {
        Directory.CreateDirectory(Path.Combine(f.State, "previous-wallpaper.json"));
        var error = Throws<Exception>(() => f.Manager.Apply(f.NewImage));
        Require(error is IOException or UnauthorizedAccessException, "Unexpected backup failure.");
        Require(f.Backend.ApplyCalls == 0, "Desktop changed without a durable backup.");
    }),
    ("Missing recovery payload prevents restore writes", f =>
    {
        f.Manager.Apply(f.NewImage);
        File.Delete(f.Saved().Monitors[0].Image);
        Throws<FileNotFoundException>(f.Manager.RestorePrevious);
        Require(f.Backend.RestoreCalls == 0, "Incomplete recovery changed the desktop.");
    }),
    ("Recovery rejects images outside its backup directory", f =>
    {
        File.WriteAllText(Path.Combine(f.State, "previous-wallpaper.json"), JsonSerializer.Serialize(f.Backend.Current));
        Throws<InvalidDataException>(f.Manager.RestorePrevious);
        Require(f.Backend.RestoreCalls == 0, "Unconfined recovery changed the desktop.");
    }),
    ("Malformed recovery metadata causes no desktop changes", f =>
    {
        File.WriteAllText(Path.Combine(f.State, "previous-wallpaper.json"), "{broken");
        Throws<JsonException>(f.Manager.RestorePrevious);
        Require(f.Backend.RestoreCalls == 0, "Malformed recovery changed the desktop.");
    }),
    ("Oversized recovery metadata is rejected before parsing", f =>
    {
        File.WriteAllText(Path.Combine(f.State, "previous-wallpaper.json"), new string(' ', 1024 * 1024 + 1));
        Throws<InvalidDataException>(f.Manager.RestorePrevious);
    }),
    ("Concurrent operations are refused without desktop writes", f =>
    {
        using var held = new FileStream(Path.Combine(f.State, "wallpaper.lock"), FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
        Throws<IOException>(() => f.Manager.Apply(f.NewImage));
        Require(f.Backend.ApplyCalls == 0, "Concurrent operation changed the desktop.");
    }),
};

foreach (var (name, run) in checks)
{
    using var fixture = new Fixture();
    run(fixture);
    Console.WriteLine($"PASS: {name}");
}
Console.WriteLine($"{checks.Length} Windows wallpaper checks passed. No real desktop settings were changed.");

static void Require(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
}

static T Throws<T>(Action action) where T : Exception
{
    try { action(); }
    catch (T error) { return error; }
    throw new InvalidOperationException($"Expected {typeof(T).Name}.");
}

sealed class Fixture : IDisposable
{
    public string Root { get; } = Path.Combine(Path.GetTempPath(), "bankai-windows-check-" + Guid.NewGuid().ToString("N"));
    public string State => Path.Combine(Root, "state");
    public string OldImage => Path.Combine(Root, "old.png");
    public string NewImage => Path.Combine(Root, "new.png");
    public FakeBackend Backend { get; }
    public WallpaperManager Manager { get; }

    public Fixture()
    {
        Directory.CreateDirectory(State);
        File.WriteAllText(OldImage, "old image");
        File.WriteAllText(NewImage, "new image");
        Backend = new FakeBackend(new WallpaperSnapshot(1, 123, 3,
            [new MonitorWallpaper("monitor-a", OldImage), new MonitorWallpaper("monitor-b", "")]));
        Manager = new WallpaperManager(State, Backend);
    }

    public WallpaperSnapshot Saved() => JsonSerializer.Deserialize<WallpaperSnapshot>(
        File.ReadAllText(Path.Combine(State, "previous-wallpaper.json")))!;
    public void Dispose() => Directory.Delete(Root, recursive: true);
}

sealed class FakeBackend(WallpaperSnapshot initial) : IWallpaperBackend
{
    public WallpaperSnapshot Current { get; private set; } = initial;
    public bool FailApply, FailRestore;
    public int ApplyCalls, RestoreCalls;
    public WallpaperSnapshot Capture() => Current;

    public void Apply(string path)
    {
        ApplyCalls++;
        Current = Current with { Position = 4, Monitors = Current.Monitors.Select(m => m with { Image = path }).ToArray() };
        if (FailApply) throw new IOException("Simulated partial apply failure.");
    }

    public void Restore(WallpaperSnapshot snapshot)
    {
        RestoreCalls++;
        if (FailRestore) throw new IOException("Simulated restore failure.");
        Current = snapshot;
    }
}
