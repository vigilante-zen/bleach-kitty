using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Bankai.Windows;

internal sealed class TerminalSettingsManager(string stateDirectory)
{
    internal const int MaximumBytes = 8 * 1024 * 1024;
    private readonly string root = Path.GetFullPath(stateDirectory);
    private sealed record Backup(int Version, string Target, string File, string BeforeHash, string AfterHash);

    public TerminalPreview Load(string path)
    {
        var fullPath = Path.GetFullPath(path);
        var original = Read(fullPath);
        return new TerminalPreview(fullPath, original, new TerminalSettingsDocument(original));
    }

    public bool CanRestore(string path) => File.Exists(Path.Combine(BackupDirectory(path), "previous.json"));

    public void Apply(TerminalPreview preview, TerminalProfile profile, TerminalScheme scheme)
    {
        using var operation = Lock();
        var after = preview.Document.WithScheme(profile, scheme);
        Commit(preview.Path, preview.Original, after);
    }

    public void Restore(TerminalPreview preview)
    {
        using var operation = Lock();
        var directory = BackupDirectory(preview.Path);
        var descriptor = Read(Path.Combine(directory, "previous.json"), 64 * 1024);
        var backup = JsonSerializer.Deserialize<Backup>(descriptor)
            ?? throw new InvalidDataException("Terminal backup metadata is empty.");
        if (backup.Version != 1 || string.IsNullOrWhiteSpace(backup.Target) || !SamePath(backup.Target, preview.Path) ||
            string.IsNullOrWhiteSpace(backup.File) || Path.GetFileName(backup.File) != backup.File ||
            !backup.File.EndsWith(".settings.json", StringComparison.Ordinal))
            throw new InvalidDataException("Terminal backup metadata is invalid.");
        if (Hash(preview.Original) != backup.AfterHash)
            throw new InvalidOperationException("Terminal settings changed after Bankai's last update. Restore was stopped to preserve your newer edits. Original settings remain in Bankai's TerminalBackups folder.");
        var before = Read(Path.Combine(directory, backup.File));
        if (Hash(before) != backup.BeforeHash) throw new InvalidDataException("The saved Terminal settings failed their integrity check.");
        _ = new TerminalSettingsDocument(before);
        Commit(preview.Path, preview.Original, before);
    }

    private void Commit(string target, byte[] expected, byte[] replacement)
    {
        if (replacement.Length > MaximumBytes) throw new InvalidDataException("The edited Terminal settings exceed the 8 MiB limit.");
        VerifyUnchanged(target, expected);
        if (replacement.AsSpan().SequenceEqual(expected)) return;
        var directory = BackupDirectory(target);
        RejectLinks(directory);
        Directory.CreateDirectory(directory);
        var pointer = Path.Combine(directory, "previous.json");
        var oldPointer = File.Exists(pointer) ? Read(pointer, 64 * 1024) : null;
        var name = Guid.NewGuid().ToString("N") + ".settings.json";
        WriteNew(Path.Combine(directory, name), expected);
        var descriptor = new Backup(1, Path.GetFullPath(target), name, Hash(expected), Hash(replacement));
        AtomicWrite(pointer, JsonSerializer.SerializeToUtf8Bytes(descriptor));
        try
        {
            VerifyUnchanged(target, expected);
            AtomicWrite(target, replacement, requireExisting: true);
        }
        catch (Exception changeError)
        {
            try
            {
                if (oldPointer is null) File.Delete(pointer);
                else AtomicWrite(pointer, oldPointer);
            }
            catch (Exception metadataError)
            {
                throw new AggregateException("Terminal update failed and backup metadata could not be reset. Saved settings remain in TerminalBackups.", changeError, metadataError);
            }
            throw;
        }
    }

    private FileStream Lock()
    {
        RejectLinks(root);
        Directory.CreateDirectory(root);
        var path = Path.Combine(root, "terminal.lock");
        RejectLinks(path);
        return new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None);
    }

    private string BackupDirectory(string target)
    {
        var path = Path.GetFullPath(target);
        if (OperatingSystem.IsWindows()) path = path.ToUpperInvariant();
        return Path.Combine(root, "TerminalBackups", Hash(Encoding.UTF8.GetBytes(path)));
    }

    private static bool SamePath(string left, string right) => string.Equals(
        Path.GetFullPath(left), Path.GetFullPath(right), OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal);
    private static string Hash(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes));

    private static void VerifyUnchanged(string path, byte[] expected)
    {
        if (!Read(path).AsSpan().SequenceEqual(expected))
            throw new InvalidOperationException("Terminal settings changed since this preview was loaded. Refresh the settings and try again.");
    }

    private static byte[] Read(string path, int maximum = MaximumBytes)
    {
        RejectLinks(path);
        if ((File.GetAttributes(path) & FileAttributes.Directory) != 0) throw new InvalidDataException("Select a Terminal settings file, not a directory.");
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        using var content = new MemoryStream();
        var buffer = new byte[8192];
        int count;
        while ((count = stream.Read(buffer, 0, Math.Min(buffer.Length, maximum + 1 - checked((int)content.Length)))) > 0)
        {
            content.Write(buffer, 0, count);
            if (content.Length > maximum) throw new InvalidDataException("The Terminal settings or backup exceed the supported size limit.");
        }
        return content.ToArray();
    }

    private static void RejectLinks(string path)
    {
        for (var current = new FileInfo(Path.GetFullPath(path)) as FileSystemInfo; current is not null;)
        {
            if (current.LinkTarget is not null || (current.Exists && (current.Attributes & FileAttributes.ReparsePoint) != 0))
                throw new InvalidDataException("Terminal settings and backups must not use symbolic links or junctions.");
            current = current switch { FileInfo file => file.Directory, DirectoryInfo directory => directory.Parent, _ => null };
        }
    }

    private static void WriteNew(string path, byte[] bytes)
    {
        RejectLinks(path);
        using var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None);
        stream.Write(bytes);
        stream.Flush(flushToDisk: true);
    }

    private static void AtomicWrite(string path, byte[] bytes, bool requireExisting = false)
    {
        RejectLinks(path);
        var temporary = path + ".bankai-" + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            WriteNew(temporary, bytes);
            RejectLinks(path);
            if (requireExisting || File.Exists(path)) File.Replace(temporary, path, null);
            else File.Move(temporary, path);
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }
}
