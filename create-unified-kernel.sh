#!/bin/sh

VARIANT=""

OUTPUT=""

handle_errors() {
	[ "$1" -eq "0" ] && return

	echo "$OUTPUT"
	exit "$1"
}

set +e

mkdir -p /efi/EFI/Linux 2> /dev/null

OUTPUT+=$(objcopy \
	--add-section .osrel="/usr/lib/os-release" --change-section-vma .osrel=0x20000 \
	--add-section .cmdline="/etc/cmdline" --change-section-vma .cmdline=0x30000 \
	--add-section .linux="/boot/vmlinuz-linux${VARIANT}" --change-section-vma .linux=0x2000000 \
	--add-section .initrd=<(cat /boot/*-ucode.img /boot/initramfs-linux${VARIANT}.img) --change-section-vma .initrd=0x3000000 \
	"/usr/lib/systemd/boot/efi/linuxx64.efi.stub" \
	"/efi/EFI/Linux/linux.efi" 2>&1)

handle_errors "$?"

OUTPUT+=$(sbsign \
	--key /etc/secureboot/keys/db/db.key \
	--cert /etc/secureboot/keys/db/db.crt \
	--output /efi/EFI/Linux/linux.efi \
	/efi/EFI/Linux/linux.efi 2>&1)

handle_errors "$?"
