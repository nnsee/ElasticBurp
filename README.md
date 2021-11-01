## Create and sign a unified EFI executable

### Description

This script (`create-unified-kernel.sh`) combines the Linux kernel and initrd images and creates a unified image which is then signed for secure boot. The image is created under `/efi/EFI/Linux/linux.efi`.

**The script makes a number of assumptions about the system.** Notably:

* The system is based on Arch Linux
* The system has boot parameters in `/boot/cmdline.txt` (minimal example provided in this repo - modify to your needs)
* The system has [secure boot keys in `/etc/secureboot`](https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot#Enrolling_keys_in_firmware)
* The system has the `sbsigntools` and `binutils` packages installed
* The system is using the stock kernel (kernel in `/boot/vmlinuz-linux` and initramfs in `/boot/initramfs-linux.img`)

Fortunately, the script is minimal - it's easy to understand and modify to your specific scenario.

You'll also need to actually use `efibootmgr` or similar to create the EFI boot entry. Something like so:
```sh
efibootmgr --create --disk /dev/nvme0n1 --part 1 --label "Arch" --loader '\EFI\Linux\linux.efi' --verbose
```

A convenience pacman hook is provided. This can be copied over:
```sh
mkdir -p /etc/pacman.d/hooks/
cp 999-sign-kernel.hook /etc/pacman.d/hooks/
```

### Use case

I have full disk crypto set up using LUKS2. The entire rootfs is encrypted, including `boot`. Decryption is handled by systemd, using the `sd-encrypt` mkinitcpio hook. I leverage secure boot and EFISTUB to combine the entire boot chain into one EFI executable and sign it, thus preventing any tampering of the boot chain before I boot into the root filesystem.
