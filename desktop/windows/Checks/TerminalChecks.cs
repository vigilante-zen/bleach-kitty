using System.Text;
using System.Text.Json;
using Bankai.Windows;

internal static class TerminalChecks
{
    private static readonly TerminalScheme Scheme = TerminalScheme.ForPreset(new Preset("rukia", "Rukia", "Ice blue", "#a9dfff", "rukia-desktop.png"));
    private static int passed;

    public static void Run()
    {
        Check("JSONC edits preserve comments, UTF-8 BOM, unknown settings and other profiles", f =>
        {
            var source = "{\r\n// 保留 my notes\r\n\"profiles\":{\"defaults\":{\"font\":{\"face\":\"Cascadia Code\"}},\"list\":[{\"name\":\"PowerShell\",\"colorScheme\":{\"dark\":\"Campbell\",\"light\":\"One Half Light\"},\"commandline\":\"pwsh.exe\",},{\"name\":\"WSL\",\"colorScheme\":\"Ubuntu\"},]},\r\n\"schemes\":[{\"name\":\"My own scheme\",\"background\":\"#123456\"},/* keep scheme note */],\"actions\":[{\"command\":\"copy\",\"keys\":\"ctrl+c\"}],\"unknown\":{\"future\":true},\r\n}";
            f.Write(Encoding.UTF8.GetPreamble().Concat(Encoding.UTF8.GetBytes(source)).ToArray());
            var preview = f.Load();
            f.Manager.Apply(preview, preview.Document.Profiles.Single(p => p.Label == "PowerShell"), Scheme);
            var changed = File.ReadAllBytes(f.Settings);
            Require(changed.AsSpan().StartsWith(Encoding.UTF8.GetPreamble()), "BOM was removed.");
            var text = File.ReadAllText(f.Settings);
            foreach (var value in new[] { "// 保留 my notes\r\n", "/* keep scheme note */", "\"font\":{\"face\":\"Cascadia Code\"}", "\"colorScheme\":\"Ubuntu\"", "\"commandline\":\"pwsh.exe\"", "\"unknown\":{\"future\":true}", "\"keys\":\"ctrl+c\"" })
                Require(text.Contains(value), "Unrelated text changed: " + value);
            using var json = Parse(changed);
            Require(json.RootElement.GetProperty("profiles").GetProperty("list")[0].GetProperty("colorScheme").GetString() == Scheme.Name, "Wrong profile was updated.");
        });
        Check("Missing root sections and defaults are added as valid JSONC", f =>
        {
            foreach (var source in new[] { "{}", "{/* retained */}", "{\"profiles\":{}}", "{\"profiles\":{\"list\":[]}, /* retained */}", "{\"profiles\":{\"defaults\":{},},}" })
            {
                var document = new TerminalSettingsDocument(Encoding.UTF8.GetBytes(source));
                using var json = Parse(document.WithScheme(document.Profiles[0], Scheme));
                Require(json.RootElement.GetProperty("schemes").GetArrayLength() == 1, "Scheme was not added.");
                Require(json.RootElement.GetProperty("profiles").GetProperty("defaults").GetProperty("colorScheme").GetString() == Scheme.Name, "Defaults were not updated.");
            }
        });
        Check("Repeated apply does not duplicate a matching Bankai scheme", f =>
        {
            var document = f.Load().Document;
            var first = document.WithScheme(document.Profiles[0], Scheme);
            var again = new TerminalSettingsDocument(first);
            var second = again.WithScheme(again.Profiles[0], Scheme);
            Require(first.AsSpan().SequenceEqual(second), "Idempotent apply changed the file again.");
        });
        Check("A conflicting user scheme is not overwritten", f =>
        {
            f.Write("{\"schemes\":[{\"name\":\"Bankai Rukia\",\"foreground\":\"#ffffff\"}]}"u8.ToArray());
            var before = File.ReadAllBytes(f.Settings);
            var preview = f.Load();
            Throws<InvalidDataException>(() => f.Manager.Apply(preview, preview.Document.Profiles[0], Scheme));
            Require(File.ReadAllBytes(f.Settings).AsSpan().SequenceEqual(before), "Conflicting scheme changed settings.");
        });
        Check("Legacy profile arrays target an explicit profile", f =>
        {
            var document = new TerminalSettingsDocument("{\"profiles\":[{\"name\":\"PowerShell\"}]}"u8.ToArray());
            Require(document.Profiles.Count == 1 && document.Profiles[0].Index == 0, "Legacy profiles offered invalid defaults.");
            using var json = Parse(document.WithScheme(document.Profiles[0], Scheme));
            Require(json.RootElement.GetProperty("profiles")[0].GetProperty("colorScheme").GetString() == Scheme.Name, "Legacy profile did not change.");
        });
        Check("Restore after reopening recovers exact original bytes and can be undone", f =>
        {
            var original = File.ReadAllBytes(f.Settings);
            var preview = f.Load();
            f.Manager.Apply(preview, preview.Document.Profiles[0], Scheme);
            var applied = File.ReadAllBytes(f.Settings);
            var reopened = new TerminalSettingsManager(f.State);
            Require(reopened.CanRestore(f.Settings), "Reopened app cannot see recovery data.");
            reopened.Restore(reopened.Load(f.Settings));
            Require(File.ReadAllBytes(f.Settings).AsSpan().SequenceEqual(original), "Restore did not preserve original bytes.");
            reopened.Restore(reopened.Load(f.Settings));
            Require(File.ReadAllBytes(f.Settings).AsSpan().SequenceEqual(applied), "Restore could not be undone.");
        });
        Check("Apply refuses a file edited after preview", f =>
        {
            var preview = f.Load();
            File.AppendAllText(f.Settings, "\n// another editor");
            var edited = File.ReadAllBytes(f.Settings);
            Throws<InvalidOperationException>(() => f.Manager.Apply(preview, preview.Document.Profiles[0], Scheme));
            Require(File.ReadAllBytes(f.Settings).AsSpan().SequenceEqual(edited), "Stale apply lost external edits.");
        });
        Check("Restore refuses newer edits made after Apply", f =>
        {
            var preview = f.Load();
            f.Manager.Apply(preview, preview.Document.Profiles[0], Scheme);
            File.AppendAllText(f.Settings, "\n// newer preference");
            var edited = File.ReadAllBytes(f.Settings);
            Throws<InvalidOperationException>(() => f.Manager.Restore(f.Load()));
            Require(File.ReadAllBytes(f.Settings).AsSpan().SequenceEqual(edited), "Restore lost newer preferences.");
        });
        Check("Corrupt recovery payload is rejected", f =>
        {
            var preview = f.Load();
            f.Manager.Apply(preview, preview.Document.Profiles[0], Scheme);
            var applied = File.ReadAllBytes(f.Settings);
            var payload = Directory.GetFiles(f.State, "*.settings.json", SearchOption.AllDirectories).Single();
            File.WriteAllText(payload, "{}");
            Throws<InvalidDataException>(() => f.Manager.Restore(f.Load()));
            Require(File.ReadAllBytes(f.Settings).AsSpan().SequenceEqual(applied), "Corrupt backup changed settings.");
        });
        Check("Backup write failure prevents settings changes", f =>
        {
            Directory.CreateDirectory(f.State);
            File.WriteAllText(Path.Combine(f.State, "TerminalBackups"), "block directory creation");
            var preview = f.Load();
            Throws<IOException>(() => f.Manager.Apply(preview, preview.Document.Profiles[0], Scheme));
            Require(File.ReadAllBytes(f.Settings).AsSpan().SequenceEqual(preview.Original), "Settings changed without a backup.");
        });
        Check("Settings reads reject oversized files", f =>
        {
            f.Write(new byte[TerminalSettingsManager.MaximumBytes + 1]);
            Throws<InvalidDataException>(() => f.Load());
        });
        Check("Malformed, duplicate-key and invalid profile settings are rejected", f =>
        {
            foreach (var source in new[] { "{", "{\"profiles\":null}", "{\"profiles\":{\"list\":false}}", "{\"profiles\":{\"defaults\":[]}}", "{\"profiles\":{},\"profiles\":{}}" })
            {
                var error = Throws<Exception>(() => new TerminalSettingsDocument(Encoding.UTF8.GetBytes(source)));
                Require(error is JsonException or InvalidDataException, "Unexpected settings validation failure.");
            }
        });
        Check("Concurrent Bankai changes are refused", f =>
        {
            Directory.CreateDirectory(f.State);
            using var held = new FileStream(Path.Combine(f.State, "terminal.lock"), FileMode.Create, FileAccess.ReadWrite, FileShare.None);
            var preview = f.Load();
            Throws<IOException>(() => f.Manager.Apply(preview, preview.Document.Profiles[0], Scheme));
            Require(File.ReadAllBytes(f.Settings).AsSpan().SequenceEqual(preview.Original), "Concurrent edit changed settings.");
        });
        Check("Different Terminal installations keep separate recovery data", f =>
        {
            var other = Path.Combine(f.Root, "preview-settings.json");
            File.WriteAllText(other, "{\"profiles\":{\"defaults\":{\"font\":{\"size\":19}}}}");
            var original = File.ReadAllBytes(other);
            var stable = f.Load();
            var preview = f.Manager.Load(other);
            f.Manager.Apply(stable, stable.Document.Profiles[0], Scheme);
            f.Manager.Apply(preview, preview.Document.Profiles[0], Scheme);
            f.Manager.Restore(f.Manager.Load(other));
            Require(File.ReadAllBytes(other).AsSpan().SequenceEqual(original), "Wrong installation was restored.");
            Require(File.ReadAllText(f.Settings).Contains(Scheme.Name), "Other installation changed during restore.");
        });
        Check("Standard installation discovery finds only existing settings", f =>
        {
            Require(TerminalSettingsDocument.Discover(f.Root).Count == 0, "Discovery invented an installation.");
            foreach (var package in new[] { "Microsoft.WindowsTerminal_8wekyb3d8bbwe", "Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe", "Microsoft.WindowsTerminalCanary_8wekyb3d8bbwe" })
            {
                var path = Path.Combine(f.Root, "Packages", package, "LocalState");
                Directory.CreateDirectory(path);
                File.WriteAllText(Path.Combine(path, "settings.json"), "{}");
            }
            var unpackaged = Path.Combine(f.Root, "Microsoft", "Windows Terminal");
            Directory.CreateDirectory(unpackaged);
            File.WriteAllText(Path.Combine(unpackaged, "settings.json"), "{}");
            Require(TerminalSettingsDocument.Discover(f.Root).Count == 4, "Discovery missed a supported installation.");
        });
        if (OperatingSystem.IsWindows())
            Check("Failed Windows replacement retains settings and earlier recovery metadata", f =>
            {
                var original = File.ReadAllBytes(f.Settings);
                var first = f.Load();
                f.Manager.Apply(first, first.Document.Profiles[0], Scheme);
                var applied = f.Load();
                var pointer = Directory.GetFiles(f.State, "previous.json", SearchOption.AllDirectories).Single();
                var descriptor = File.ReadAllBytes(pointer);
                var other = TerminalScheme.ForPreset(new Preset("ichigo", "Ichigo", "Orange", "#ff9d52", "ichigo.png"));
                using (var held = new FileStream(f.Settings, FileMode.Open, FileAccess.Read, FileShare.Read))
                    Throws<IOException>(() => f.Manager.Apply(applied, applied.Document.Profiles[0], other));
                Require(File.ReadAllBytes(f.Settings).AsSpan().SequenceEqual(applied.Original), "Failed replacement changed settings.");
                Require(File.ReadAllBytes(pointer).AsSpan().SequenceEqual(descriptor), "Earlier recovery metadata was lost.");
                f.Manager.Restore(f.Load());
                Require(File.ReadAllBytes(f.Settings).AsSpan().SequenceEqual(original), "Earlier recovery stopped working.");
            });
        else
            Check("Symlinked settings and parent directories are refused", f =>
            {
                var link = Path.Combine(f.Root, "linked.json");
                File.CreateSymbolicLink(link, f.Settings);
                Throws<InvalidDataException>(() => f.Manager.Load(link));
                var alias = Path.Combine(f.Root, "alias");
                Directory.CreateSymbolicLink(alias, Path.GetDirectoryName(f.Settings)!);
                Throws<InvalidDataException>(() => f.Manager.Load(Path.Combine(alias, Path.GetFileName(f.Settings))));
            });
        Console.WriteLine($"{passed} Terminal settings checks passed. No real Terminal settings were changed.");
    }

    private static void Check(string name, Action<TerminalFixture> action)
    {
        using var fixture = new TerminalFixture();
        action(fixture);
        passed++;
        Console.WriteLine("PASS: " + name);
    }

    private static JsonDocument Parse(byte[] bytes) => JsonDocument.Parse(
        bytes.AsSpan().StartsWith(Encoding.UTF8.GetPreamble()) ? bytes[3..] : bytes,
        new JsonDocumentOptions { CommentHandling = JsonCommentHandling.Skip, AllowTrailingCommas = true });

    private static void Require(bool value, string message)
    {
        if (!value) throw new InvalidOperationException(message);
    }

    private static T Throws<T>(Action action) where T : Exception
    {
        try { action(); }
        catch (T error) { return error; }
        throw new InvalidOperationException($"Expected {typeof(T).Name}.");
    }
}

internal sealed class TerminalFixture : IDisposable
{
    public string Root { get; } = Path.Combine(Path.GetTempPath(), "bankai-terminal-check-" + Guid.NewGuid().ToString("N"));
    public string State => Path.Combine(Root, "state");
    public string Settings => Path.Combine(Root, "terminal", "settings.json");
    public TerminalSettingsManager Manager { get; }
    public TerminalFixture()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(Settings)!);
        File.WriteAllText(Settings, "{ // user notes\n\"profiles\":{\"defaults\":{},\"list\":[{\"name\":\"PowerShell\",\"colorScheme\":\"Campbell\"}]},\"schemes\":[]}");
        Manager = new TerminalSettingsManager(State);
    }
    public TerminalPreview Load() => Manager.Load(Settings);
    public void Write(byte[] data) => File.WriteAllBytes(Settings, data);
    public void Dispose() => Directory.Delete(Root, recursive: true);
}
