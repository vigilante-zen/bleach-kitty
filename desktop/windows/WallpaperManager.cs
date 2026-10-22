using System.Security.Cryptography;
using System.Text.Json;

namespace Bankai.Windows;

internal sealed record MonitorWallpaper(string MonitorId, string Image);
internal sealed record WallpaperSnapshot(int Version, uint BackgroundColor, int Position, MonitorWallpaper[] Monitors);

internal interface IWallpaperBackend
{
    WallpaperSnapshot Capture();
    void Apply(string path);
    void Restore(WallpaperSnapshot snapshot);
}

internal sealed class WallpaperManager(string stateDirectory, IWallpaperBackend backend)
{
    private readonly string root = Path.GetFullPath(stateDirectory);
    private string PreviousPath => Path.Combine(root, "previous-wallpaper.json");
    public bool CanRestore => File.Exists(PreviousPath);

    public void Apply(string image)
    {
        using var operation = Lock();
        if (!File.Exists(image)) throw new FileNotFoundException("The selected wallpaper is missing.", image);
        // Keep an independent copy so moving the portable app does not remove the wallpaper.
        var wallpapers = Path.Combine(root, "Wallpapers");
        Directory.CreateDirectory(wallpapers);
        using var stream = File.OpenRead(image);
        var name = Convert.ToHexString(SHA256.HashData(stream)) + Path.GetExtension(image);
        var installed = Path.Combine(wallpapers, name);
        if (!File.Exists(installed)) File.Copy(image, installed);
        var before = Backup();
        SavePrevious(before);
        Change(() => backend.Apply(installed), before);
    }

    public void RestorePrevious()
    {
        using var operation = Lock();
        WallpaperSnapshot target;
        using (var stream = File.OpenRead(PreviousPath))
        {
            if (stream.Length > 1024 * 1024) throw new InvalidDataException("The wallpaper backup is too large.");
            target = JsonSerializer.Deserialize<WallpaperSnapshot>(stream)
                ?? throw new InvalidDataException("The wallpaper backup is empty.");
        }
        Validate(target, requireBackupPaths: true);
        var before = Backup();
        SavePrevious(before);
        Change(() => backend.Restore(target), before);
    }

    private FileStream Lock()
    {
        Directory.CreateDirectory(root);
        return new FileStream(Path.Combine(root, "wallpaper.lock"), FileMode.OpenOrCreate,
            FileAccess.ReadWrite, FileShare.None);
    }

    private WallpaperSnapshot Backup()
    {
        var current = backend.Capture();
        Validate(current, requireBackupPaths: false);
        var directory = Path.Combine(root, "WallpaperBackups", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(directory);
        var copies = current.Monitors.Select((monitor, index) =>
        {
            if (monitor.Image.Length == 0) return monitor;
            var copy = Path.Combine(directory, $"{index}{Path.GetExtension(monitor.Image)}");
            File.Copy(monitor.Image, copy);
            return monitor with { Image = copy };
        }).ToArray();
        var backup = current with { Monitors = copies };
        File.WriteAllText(Path.Combine(directory, "snapshot.json"), JsonSerializer.Serialize(backup));
        return backup;
    }

    private void SavePrevious(WallpaperSnapshot snapshot)
    {
        var temporary = PreviousPath + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                JsonSerializer.Serialize(stream, snapshot);
                stream.Flush(flushToDisk: true);
            }
            File.Move(temporary, PreviousPath, overwrite: true);
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
    }

    private void Change(Action change, WallpaperSnapshot before)
    {
        try { change(); }
        catch (Exception changeError)
        {
            try { backend.Restore(before); }
            catch (Exception restoreError)
            {
                throw new AggregateException("Wallpaper change and automatic recovery failed. The backup is saved in Bankai's local app data.", changeError, restoreError);
            }
            throw;
        }
    }

    private void Validate(WallpaperSnapshot snapshot, bool requireBackupPaths)
    {
        if (snapshot.Version != 1 || snapshot.Position is < 0 or > 5 ||
            snapshot.Monitors is null || snapshot.Monitors.Length is < 1 or > 64 ||
            snapshot.Monitors.Any(m => m is null || string.IsNullOrWhiteSpace(m.MonitorId) || m.Image is null) ||
            snapshot.Monitors.Select(m => m.MonitorId).Distinct(StringComparer.Ordinal).Count() != snapshot.Monitors.Length)
            throw new InvalidDataException("The wallpaper backup is invalid.");
        var backupRoot = Path.Combine(root, "WallpaperBackups") + Path.DirectorySeparatorChar;
        foreach (var monitor in snapshot.Monitors)
        {
            if (monitor.Image.Length == 0) continue; // Solid-color desktop.
            if (requireBackupPaths && !Path.GetFullPath(monitor.Image).StartsWith(backupRoot, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("A wallpaper backup image is outside Bankai's backup directory.");
            if (!File.Exists(monitor.Image)) throw new FileNotFoundException("A previous wallpaper image is missing; no desktop changes were made.", monitor.Image);
        }
    }
}
