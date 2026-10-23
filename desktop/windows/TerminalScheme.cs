namespace Bankai.Windows;

internal sealed record TerminalScheme(string Name, IReadOnlyDictionary<string, string> Colors)
{
    public static TerminalScheme ForPreset(Preset preset)
    {
        if (preset.Accent.Length != 7 || preset.Accent[0] != '#' ||
            !preset.Accent[1..].All(Uri.IsHexDigit))
            throw new InvalidDataException("The character accent is not a valid color.");
        // Match Bankai's Kitty palette and desktop accent overrides (ANSI red/bright red, cursor and selection).
        return new TerminalScheme("Bankai " + preset.Title, new Dictionary<string, string>
        {
            ["background"] = "#090C12", ["foreground"] = "#E8EDF5",
            ["cursorColor"] = preset.Accent, ["selectionBackground"] = preset.Accent,
            ["black"] = "#090C12", ["red"] = preset.Accent, ["green"] = "#76D7C4", ["yellow"] = "#F0C674",
            ["blue"] = "#65C9FF", ["purple"] = "#BB86FC", ["cyan"] = "#59D8E8", ["white"] = "#E8EDF5",
            ["brightBlack"] = "#586477", ["brightRed"] = preset.Accent, ["brightGreen"] = "#9AE8D8", ["brightYellow"] = "#FFE29A",
            ["brightBlue"] = "#91DCFF", ["brightPurple"] = "#D1A5FF", ["brightCyan"] = "#8BE9F5", ["brightWhite"] = "#FFFFFF",
        });
    }

    public Dictionary<string, string> ToSettings() => new(Colors) { ["name"] = Name };
}
