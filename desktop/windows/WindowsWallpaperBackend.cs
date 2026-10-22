using System.Runtime.InteropServices;

namespace Bankai.Windows;

internal sealed class WindowsWallpaperBackend : IWallpaperBackend, IDisposable
{
    private readonly IDesktopWallpaper desktop = (IDesktopWallpaper)Activator.CreateInstance(
        Type.GetTypeFromCLSID(new Guid("C2CF3110-460E-4FC1-B9D0-8A1C0C9CC4BD"), throwOnError: true)!)!;

    public WallpaperSnapshot Capture()
    {
        desktop.GetStatus(out var status);
        if ((status & 1) != 0)
            throw new InvalidOperationException("Choose a static Picture or Solid color background in Windows Settings before using Bankai. Slideshow backgrounds are not supported yet.");
        desktop.GetMonitorDevicePathCount(out var count);
        if (count is 0 or > 64) throw new InvalidOperationException("No supported desktop monitor configuration was found.");
        var monitors = new MonitorWallpaper[count];
        for (uint index = 0; index < count; index++)
        {
            desktop.GetMonitorDevicePathAt(index, out var monitor);
            desktop.GetWallpaper(monitor, out var image);
            monitors[index] = new MonitorWallpaper(monitor, image);
        }
        desktop.GetBackgroundColor(out var color);
        desktop.GetPosition(out var position);
        return new WallpaperSnapshot(1, color, position, monitors);
    }

    public void Apply(string path)
    {
        desktop.SetPosition(4); // DWPOS_FILL
        desktop.SetWallpaper(null, path);
    }

    public void Restore(WallpaperSnapshot snapshot)
    {
        // Reject changed monitor layouts before making any restoration writes.
        var current = Capture();
        var connected = current.Monitors.Select(m => m.MonitorId).ToHashSet(StringComparer.Ordinal);
        if (!connected.SetEquals(snapshot.Monitors.Select(m => m.MonitorId)))
            throw new InvalidOperationException("The monitor layout has changed. Reconnect the original monitors before restoring this wallpaper backup.");
        desktop.SetBackgroundColor(snapshot.BackgroundColor);
        desktop.SetPosition(snapshot.Position);
        foreach (var monitor in snapshot.Monitors)
            desktop.SetWallpaper(monitor.MonitorId, monitor.Image);
    }

    public void Dispose() => Marshal.FinalReleaseComObject(desktop);

    // Preserve the native vtable order, including unused slideshow slots.
    // https://learn.microsoft.com/windows/win32/api/shobjidl_core/nn-shobjidl_core-idesktopwallpaper
    [ComImport, Guid("B92B56A9-8B55-4E14-9A89-0199BBB6F93B"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IDesktopWallpaper
    {
        void SetWallpaper([MarshalAs(UnmanagedType.LPWStr)] string? monitor, [MarshalAs(UnmanagedType.LPWStr)] string image);
        void GetWallpaper([MarshalAs(UnmanagedType.LPWStr)] string monitor, [MarshalAs(UnmanagedType.LPWStr)] out string image);
        void GetMonitorDevicePathAt(uint index, [MarshalAs(UnmanagedType.LPWStr)] out string monitor);
        void GetMonitorDevicePathCount(out uint count);
        void GetMonitorRECT([MarshalAs(UnmanagedType.LPWStr)] string monitor, out NativeRect rectangle);
        void SetBackgroundColor(uint color);
        void GetBackgroundColor(out uint color);
        void SetPosition(int position);
        void GetPosition(out int position);
        void SetSlideshow(IntPtr items);
        void GetSlideshow(out IntPtr items);
        void SetSlideshowOptions(uint options, uint milliseconds);
        void GetSlideshowOptions(out uint options, out uint milliseconds);
        void AdvanceSlideshow([MarshalAs(UnmanagedType.LPWStr)] string monitor, int direction);
        void GetStatus(out uint state);
        void Enable([MarshalAs(UnmanagedType.Bool)] bool enable);
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct NativeRect { public int Left, Top, Right, Bottom; }
}
