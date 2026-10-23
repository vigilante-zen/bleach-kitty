using System.Text.Json;

namespace Bankai.Windows;

internal sealed record TerminalProfile(int Index, string Label);
internal sealed record TerminalInstallation(string Label, string Path);
internal sealed record TerminalPreview(string Path, byte[] Original, TerminalSettingsDocument Document);

internal sealed class TerminalSettingsDocument
{
    private readonly byte[] source;
    public IReadOnlyList<TerminalProfile> Profiles { get; }

    public TerminalSettingsDocument(byte[] source)
    {
        this.source = source;
        var editor = new JsoncEditor(source);
        var profiles = FindProfiles(editor.Root);
        var choices = new List<TerminalProfile>();
        var profileObject = editor.Root.Properties.GetValueOrDefault("profiles");
        if (profileObject?.Type != JsonTokenType.StartArray)
            choices.Add(new TerminalProfile(-1, "Profile defaults (individual overrides remain)"));
        for (var index = 0; index < profiles.Count; index++)
        {
            var profile = profiles[index];
            if (profile.Type != JsonTokenType.StartObject) throw new InvalidDataException("A Terminal profile is not an object.");
            var name = profile.Properties.GetValueOrDefault("name")?.Text ??
                profile.Properties.GetValueOrDefault("guid")?.Text ?? $"Profile {index + 1}";
            choices.Add(new TerminalProfile(index, name));
        }
        Profiles = choices;
    }

    private static List<JsoncEditor.Node> FindProfiles(JsoncEditor.Node root)
    {
        if (!root.Properties.TryGetValue("profiles", out var profiles)) return [];
        if (profiles.Type == JsonTokenType.StartArray) return profiles.Items; // Older Terminal format.
        if (profiles.Type != JsonTokenType.StartObject) throw new InvalidDataException("Terminal profiles must be an object or array.");
        if (profiles.Properties.TryGetValue("defaults", out var defaults) && defaults.Type != JsonTokenType.StartObject)
            throw new InvalidDataException("Terminal profile defaults must be an object.");
        if (!profiles.Properties.TryGetValue("list", out var list)) return [];
        if (list.Type != JsonTokenType.StartArray) throw new InvalidDataException("Terminal profile list must be an array.");
        return list.Items;
    }

    public byte[] WithScheme(TerminalProfile profile, TerminalScheme scheme)
    {
        var editor = new JsoncEditor(source);
        var root = editor.Root;
        var list = FindProfiles(root);
        if (!Profiles.Contains(profile)) throw new InvalidOperationException("Refresh and choose a valid Terminal profile.");
        var colors = scheme.ToSettings();
        if (root.Properties.TryGetValue("schemes", out var schemes))
        {
            if (schemes.Type != JsonTokenType.StartArray) throw new InvalidDataException("Terminal color schemes must be an array.");
            if (schemes.Items.Any(item => item.Type != JsonTokenType.StartObject ||
                string.IsNullOrWhiteSpace(item.Properties.GetValueOrDefault("name")?.Text)))
                throw new InvalidDataException("Terminal color schemes must be named objects.");
            var matching = schemes.Items.Where(item => item.Properties.GetValueOrDefault("name")?.Text == scheme.Name).ToArray();
            if (matching.Length > 1 || (matching.Length == 1 && colors.Any(pair =>
                !string.Equals(matching[0].Properties.GetValueOrDefault(pair.Key)?.Text, pair.Value, StringComparison.OrdinalIgnoreCase))))
                throw new InvalidDataException($"A different scheme named '{scheme.Name}' already exists. Rename it in Terminal before applying this scheme.");
            if (matching.Length == 0) editor.Append(schemes, colors);
        }
        else editor.Set(root, "schemes", new[] { colors });

        if (profile.Index >= 0) editor.Set(list[profile.Index], "colorScheme", scheme.Name);
        else if (!root.Properties.TryGetValue("profiles", out var profiles))
            editor.Set(root, "profiles", new { defaults = new { colorScheme = scheme.Name } });
        else if (!profiles.Properties.TryGetValue("defaults", out var defaults))
            editor.Set(profiles, "defaults", new { colorScheme = scheme.Name });
        else editor.Set(defaults, "colorScheme", scheme.Name);
        var result = editor.Finish();
        _ = new TerminalSettingsDocument(result); // Validate the edited JSONC before any writes.
        return result;
    }

    public static IReadOnlyList<TerminalInstallation> Discover(string localAppData)
    {
        var locations = new[]
        {
            new TerminalInstallation("Windows Terminal", Path.Combine(localAppData, "Packages", "Microsoft.WindowsTerminal_8wekyb3d8bbwe", "LocalState", "settings.json")),
            new TerminalInstallation("Windows Terminal Preview", Path.Combine(localAppData, "Packages", "Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe", "LocalState", "settings.json")),
            new TerminalInstallation("Windows Terminal Canary", Path.Combine(localAppData, "Packages", "Microsoft.WindowsTerminalCanary_8wekyb3d8bbwe", "LocalState", "settings.json")),
            new TerminalInstallation("Windows Terminal (unpackaged)", Path.Combine(localAppData, "Microsoft", "Windows Terminal", "settings.json")),
        };
        return locations.Where(item => File.Exists(item.Path)).ToArray();
    }
}
