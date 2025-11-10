# Running Linux on Windows and Lenovo Hardware

This document covers two complementary scenarios:

1. Deploying Arch Linux with Windows Subsystem for Linux 2 (WSL 2) for a lightweight, terminal-friendly environment inside
   Windows.
2. Dual-booting Linux distributions—Arch, Ubuntu, Debian, and more—alongside Windows 10/11 on Lenovo laptops or desktops.

Whether you prefer the flexibility of WSL or the full native performance of bare-metal installations, the guidance below
highlights key prerequisites, installation steps, and troubleshooting advice tailored for both workflows.

---

## Part I – Arch Linux on WSL 2

### Prerequisites

- **Windows build**: Windows 10 2004 (build 19041) or newer, or any release of Windows 11.
- **WSL 2 enabled**: Turn on the *Virtual Machine Platform* and *Windows Subsystem for Linux* optional features, then set WSL 2
  as the default version.
- **Administrative rights**: Needed for enabling Windows features and importing the Arch image.
- **Disk space**: Allocate at least 10&nbsp;GB for the Arch root filesystem.

#### Enable WSL 2

Open **PowerShell as Administrator** and run:

```powershell
wsl --install
wsl --set-default-version 2
```

If WSL is already installed, double-check that virtualization is enabled in BIOS/UEFI and update the kernel when prompted:

```powershell
wsl --update
```

### Install Arch Linux on WSL 2

1. **Download an Arch root filesystem**
   - Grab the latest `Arch.zip` release from the official [ArchWSL project](https://github.com/yuk7/ArchWSL/releases) or create
     your own tarball from an Arch ISO with `pacstrap`.
2. **Import the distribution into WSL**
   - Choose an install directory (for example, `C:\Distros\Arch`).
   - In PowerShell, import the tarball:

     ```powershell
     wsl --import Arch C:\Distros\Arch .\Arch.zip --version 2
     ```

3. **Launch Arch and create a user**
   - Start the instance and provision accounts:

     ```powershell
     wsl -d Arch
     useradd -m -G wheel <your-username>
     passwd <your-username>
     passwd
     echo "%wheel ALL=(ALL:ALL) ALL" >> /etc/sudoers.d/wheel
     ```

### Initial Configuration (WSL 2)

Inside the Arch shell, refresh keys and mirrors, then update the system:

```bash
sudo pacman-key --init
sudo pacman-key --populate archlinux
sudo pacman -Syu --noconfirm
```

Configure locale, timezone, and shell preferences as needed. To enable `systemd` support (available in newer WSL builds), add the
following to `/etc/wsl.conf`:

```ini
[boot]
systemd=true
```

Shutdown the instance with `wsl --terminate Arch`, then relaunch it to activate `systemd`.

### Working with the WSL Filesystem

- The WSL filesystem lives within the VHDX file located in your chosen install directory.
- Access Windows files from `/mnt/c`, `/mnt/d`, and similar mount points.
- Use `\\wsl$\Arch` in File Explorer to browse the Linux filesystem from Windows.

### Package Management Tips

- Update frequently to stay current: `sudo pacman -Syu`.
- Install `base-devel` if you plan to build packages from the Arch User Repository (AUR).
- Consider helpers like `paru` or `yay` for AUR packages—install them manually following Arch packaging guidelines.

### Networking and Interop

- Use `ip addr` to inspect virtual network interfaces; WSL provides a NAT-ed adapter by default.
- Windows and WSL share the same network stack, so services bound to `0.0.0.0` are reachable from Windows via `localhost`.
- Launch Windows apps from WSL with `explorer.exe .` or `notepad.exe file.txt`.

### Backups and Exporting

Back up your Arch distro by exporting it to a tarball:

```powershell
wsl --export Arch C:\Backups\arch-$(Get-Date -Format yyyyMMdd).tar
```

Restore the backup with `wsl --import`, pointing at the exported tarball.

### Troubleshooting (WSL 2)

| Symptom | Resolution |
| --- | --- |
| `WslRegisterDistribution failed with error 0x80370102` | Enable virtualization (Intel VT-x / AMD-V) in firmware and ensure Hyper-V services are running. |
| No internet connectivity | Disable conflicting VPN software or set DNS manually in `/etc/resolv.conf`. |
| Clock drift | Run `hwclock --systohc` inside Arch or enable `systemd-timesyncd` when using `systemd`. |

### Additional Resources (WSL 2)

- [Microsoft: WSL documentation](https://learn.microsoft.com/windows/wsl/)
- [ArchWSL project](https://github.com/yuk7/ArchWSL)
- [Arch Linux Wiki: WSL](https://wiki.archlinux.org/title/WSL)

---

## Part II – Dual-Booting Linux on Lenovo Hardware

If you are ready for a full native experience, Lenovo laptops and desktops generally handle Linux dual-boot well when you plan
the disk layout and firmware settings ahead of time. The following guidance applies to systems that already run Windows 10 or 11
and can also accommodate multiple Linux distributions.

### Hardware Preparation Checklist

- **BIOS/UEFI firmware**: Update to the latest release from Lenovo Support. Newer firmware often improves ACPI, keyboard,
  touchpad, and power-management compatibility.
- **Secure Boot**: Most modern distributions support Secure Boot, but if you encounter issues you can disable it temporarily in
  the BIOS (usually under *Security ▸ Secure Boot*).
- **Storage mode**: Confirm that your NVMe/SATA controller is set to AHCI. If Windows was installed in RAID/Intel RST mode,
  switch to AHCI after enabling Safe Mode once in Windows to avoid boot failures.
- **Free space**: Plan at least 30&nbsp;GB of unallocated space for each Linux distribution you intend to install. Use Windows
  Disk Management to shrink existing partitions before booting installers.
- **Firmware keys**: Note the Lenovo-specific boot menu key (typically `F12`) and BIOS setup key (`F1` or `F2`).

### Creating Installation Media

1. Download ISO images:
   - **Arch Linux** – Rolling release with a minimal, command-driven installer.
   - **Ubuntu 22.04 LTS / 24.04 LTS** – Friendly graphical installer with broad hardware support.
   - **Debian 12 (Bookworm)** – Offers both text-mode and graphical installers with stable packages.
   - Consider **Fedora Workstation**, **openSUSE Tumbleweed**, or **EndeavourOS** if you want polished installers while retaining
     powerful terminals.
2. Use [Rufus](https://rufus.ie) or the [Fedora Media Writer](https://getfedora.org) on Windows to write each ISO to a USB drive.
   Enable the *GPT + UEFI* option to match modern Lenovo firmware.
3. Safely eject the USB media before rebooting.

### Dual-Boot Installation Flow

1. **Boot to firmware** using `F12`, then choose the USB installer.
2. **Partitioning strategy**:
   - Leave the existing EFI System Partition (ESP) intact; each Linux installer will add entries to it.
   - Create new ext4 partitions (or btrfs if preferred) within the free space. Optionally add a swap partition (8–16&nbsp;GB).
   - For multiple distributions, create separate root partitions (e.g., `ArchRoot`, `UbuntuRoot`) and a shared `/home` if desired.
3. **Install your first distribution** (e.g., Ubuntu) using its graphical installer. Verify that GRUB detects Windows.
4. **Install additional distributions** one at a time. For Arch, follow the guided steps below; for Debian/Ubuntu, choose the
   manual partitioning option and reuse the same ESP.
5. **Set default boot order** in BIOS or via `efibootmgr` from Linux after installations.

### Sample Arch Dual-Boot Steps

```bash
# In the Arch ISO live environment
timedatectl set-ntp true
lsblk                        # identify target disk, e.g., /dev/nvme0n1
fdisk /dev/nvme0n1           # create/assign partitions if needed
mkfs.ext4 /dev/nvme0n1p6     # format the Arch root partition
mount /dev/nvme0n1p6 /mnt
mount /dev/nvme0n1p1 /mnt/boot   # existing EFI partition
pacstrap /mnt base linux linux-firmware networkmanager
genfstab -U /mnt >> /mnt/etc/fstab
arch-chroot /mnt
ln -sf /usr/share/zoneinfo/Region/City /etc/localtime
hwclock --systohc
echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
locale-gen
echo "arch-lenovo" > /etc/hostname
passwd
useradd -m -G wheel youruser
passwd youruser
pacman -S grub efibootmgr networkmanager sudo vim
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=Arch
grub-mkconfig -o /boot/grub/grub.cfg
systemctl enable NetworkManager
exit
umount -R /mnt
reboot
```

Repeat similar steps for other distributions, ensuring GRUB entries remain intact.

### Post-Install Tweaks for Lenovo Systems

- **Firmware updates**: Install `fwupd` (`sudo fwupdmgr refresh && sudo fwupdmgr update`) to receive Lenovo BIOS and peripheral
  updates directly from Linux.
- **Input devices**: For IdeaPad/ThinkPad touchpads, install `libinput` (already default on most distros) and enable gestures via
  `gnome-tweaks` or `libinput-gestures`.
- **Function keys**: Add kernel parameters such as `acpi_backlight=vendor` if brightness controls misbehave.
- **Power profiles**: Install `tlp` or `power-profiles-daemon` to balance battery life vs. performance.
- **Firmware-specific drivers**: ThinkPads often benefit from the `thinkfan` service and `fw-ectool` for advanced thermal
  management.

### Interactive Terminal Installers Worth Trying

- **Archinstall** (included with recent Arch ISOs): Provides guided partitioning, desktop selection, and user creation while
  keeping the Arch philosophy.
- **Debian Text Installer**: A proven curses-based interface that walks through language, partitioning, task selection, and GRUB
  setup.
- **Ubuntu Server Installer**: Offers a TUI with cloud-init integration—great for a keyboard-driven setup that still configures
  desktop packages later.
- **EndeavourOS**: Ships with the `Calamares` graphical installer plus an *offline* and *online* mode with TUI helpers.
- **Fedora Minimal ISO**: Uses the Anaconda text mode for scripted, repeatable installs.

These tools blend terminal-friendly workflows with sensible defaults, making them ideal for experimenting on Lenovo hardware
without losing the tactile keyboard-centric experience.

### Maintaining a Healthy Dual-Boot System

- Keep Windows and Linux bootloaders aligned: after major Windows updates, boot into Linux and run `sudo grub-mkconfig -o
  /boot/grub/grub.cfg` to refresh entries.
- Use the Lenovo Vantage (Windows) or `fwupd` (Linux) utilities regularly for firmware patches.
- Back up the EFI partition before major changes using `dd if=/dev/nvme0n1p1 of=esp-backup.img`.
- Document which partition holds each distribution. Tools like `lsblk`, `blkid`, or `gnome-disks` help verify before making
  changes.
- For quick recovery, create a Ventoy USB stick with multiple ISOs and keep it handy.

### Troubleshooting (Dual-Boot)

| Symptom | Resolution |
| --- | --- |
| System skips GRUB and boots straight to Windows | Re-enable the Linux boot entry in BIOS or run `bcdedit /set {bootmgr} path \\EFI\\GRUB\\grubx64.efi` from an elevated PowerShell. |
| Black screen after selecting Linux | Add `nomodeset` temporarily, then install proprietary GPU drivers (e.g., NVIDIA) or adjust `i915` parameters for Intel graphics. |
| Touchpad not detected | Enable `i2c-hid` in BIOS if available, or add `psmouse.synaptics_intertouch=1` to the kernel command line. |
| Clock differences between Windows and Linux | Set Windows to use UTC via `reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\TimeZoneInformation" /v RealTimeIsUniversal /t REG_DWORD /d 1 /f` and ensure `timedatectl set-local-rtc 0` in Linux. |
| BitLocker prompt after installing Linux | Suspend BitLocker in Windows before making partition changes, then resume once complete. |

### Additional Resources (Dual-Boot)

- [Lenovo Linux Certification Matrix](https://support.lenovo.com/us/en/solutions/pd031426)
- [Arch Wiki: Dual boot with Windows](https://wiki.archlinux.org/title/Dual_boot_with_Windows)
- [Ubuntu: Dual-boot with Windows](https://help.ubuntu.com/community/WindowsDualBoot)
- [Debian Installation Guide](https://www.debian.org/releases/stable/installmanual)

