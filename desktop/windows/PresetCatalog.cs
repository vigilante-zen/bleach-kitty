using System.Text.Json;

namespace Bankai.Windows;

public sealed record Preset(string Id, string Title, string Subtitle, string Accent, string Image);

internal static class PresetCatalog
{
    public static IReadOnlyList<Preset> Load()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Assets", "presets.json");
        using var stream = File.OpenRead(path);
        using var document = JsonDocument.Parse(stream);
        return document.RootElement.GetProperty("presets").EnumerateArray()
            .Select(item => new Preset(
                item.GetProperty("id").GetString()!,
                item.GetProperty("title").GetString()!,
                item.GetProperty("subtitle").GetString()!,
                item.GetProperty("accent").GetString()!,
                item.GetProperty("image").GetString()!))
            .ToArray();
    }

    public static string WallpaperPath(Preset preset)
    {
        if (Path.GetFileName(preset.Image) != preset.Image)
            throw new InvalidDataException("Wallpaper must be a file name.");
        return Path.Combine(AppContext.BaseDirectory, "Assets", "Wallpapers", preset.Image);
    }
}
