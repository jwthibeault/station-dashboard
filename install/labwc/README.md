# labwc Configuration

This directory contains the custom `labwc` configuration required for the
James City Bruton Volunteer Fire Department Station Dashboard.

These files are installed in the user's home directory under:

```
~/.config/labwc/
```

---

## Files

### autostart

Starts the desktop components required by the dashboard.

It is responsible for:

- Starting `kanshi`
- Running `lxsession-xdg-autostart`
- Launching Chromium using:

```
~/station-dashboard/scripts/start-browser.sh
```

- Automatically hiding the mouse cursor after startup using `wtype`

---

### rc.xml

Extends the default `labwc` keyboard configuration.

It adds one custom keybinding:

```
Alt + Super + H
```

This keybinding executes:

- `HideCursor`
- `WarpCursor`

to hide the mouse pointer and move it off-screen.

The default `labwc` keyboard shortcuts are preserved using:

```xml
<default />
```

No other keyboard shortcuts are modified.

---

## Why this is needed

The traditional Linux utility `unclutter` only works with X11.

The Station Dashboard runs under:

- Wayland
- labwc

Instead of using compatibility layers or background daemons, the dashboard uses
labwc's native cursor hiding capability.

The cursor is hidden automatically during startup by simulating the
`Alt + Super + H` key combination using `wtype`.

This approach:

- Uses native Wayland functionality
- Does not require X11
- Does not require `unclutter`
- Has proven reliable during testing

---

## Installing

Copy the files into:

```
~/.config/labwc/
```

Example:

```bash
cp autostart ~/.config/labwc/
cp rc.xml ~/.config/labwc/
```

Reload labwc:

```bash
labwc --reconfigure
```

or simply reboot.

---

## Dependencies

The automatic cursor hiding requires:

```
wtype
```

Install with:

```bash
sudo apt install wtype
```

---

## Version

Added in:

**Version 1.1.0**

Native Wayland cursor hiding.
