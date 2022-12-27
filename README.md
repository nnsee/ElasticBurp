## Create and sign a unified EFI executable

### Description

This script (`create-unified-kernel.sh`) combines the Linux kernel and initrd images and creates a unified image which is then signed for secure boot. `systemd-measure` is used in order to sign a TPM2 PCR signature which is appended to the image. The image is created under `/efi/EFI/Linux/linux.efi`.

**The script makes a number of assumptions about the system.** Notably:

* The system is based on Arch Linux
* The system has boot parameters in `/etc/cmdline` (minimal example provided in this repo - modify to your needs)
* The system has [secure boot keys in `/etc/secureboot`](https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot#Enrolling_keys_in_firmware)
* The system has the `sbsigntools` and `binutils` packages installed
* The system is using the stock kernel (kernel in `/boot/vmlinuz-linux` and initramfs in `/boot/initramfs-linux.img`)
* The system has the PCR RSA private and public keys at `/etc/systemd/tpm2-pcr-private-key.pem` and `/etc/systemd/tpm2-pcr-public-key.pem` respectively. These can be generated using `openssl`:
```
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out /etc/systemd/tpm2-pcr-private-key.pem
openssl rsa -pubout -in /etc/systemd/tpm2-pcr-private-key.pem -out /etc/systemd/tpm2-pcr-public-key.pem
```

Fortunately, the script is minimal - it's easy to understand and modify to your specific scenario. Specifically, the `VARIANT` variable defined at the top of the script is probably of most interest to you - this can be used to specify custom kernel builds, a la `VARIANT="-zen"`. Other file paths are also provided on top of the file.

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
