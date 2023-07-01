#!/bin/bash
INSTALLDEV=/dev/sda
PROFILE=default/linux/amd64/17.1/desktop
TIMEZONE=America/Los_Angeles
LOCALE=en_US.utf8
HOSTNAME=blackbriar
INTERFACES="eth0"
USERNAME=ajaso
PASSWORD=chang3m3
DONE_TIMEOUT=5

STAGE3NAME=stage3-amd64-openrc-20220814T170533Z.tar.xz
STAGE3URL=https://mirror.leaseweb.com/gentoo/releases/amd64/autobuilds/current-stage3-amd64-openrc/$STAGE3NAME
mkdir -p /mnt/gentoo
mount ${INSTALLDEV}2 /mnt/gentoo
cd /mnt/gentoo
wget $STAGE3URL
tar -xpvf $STAGE3NAME --xattrs-include='\*.\*' --numeric-owner
cp /etc/portage/make.conf /mnt/gentoo/etc/portage/make.conf
sed -iE 's/^COMMON_FLAGS="(.+)"/COMMON_FLAGS="-march=native \1"/' /mnt/gentoo/etc/portage/make.conf
cat >> /mnt/gentoo/etc/portage/make.conf <<EOF
EMERGE_DEFAULT_OPTS="\${EMERGE_DEFAULT_OPTS} --load-average=$(nproc) --jobs=1"
MAKEOPTS="-j"$(nproc)"
NINJAOPTS="-j"$(nproc)"
GRUB_PLATFORMS="efi-64"
ACCEPT_LICENSE="*"
ACCEPT_KEYWORDS="~amd64"
GENTOO_MIRRORS="http://gentoo.cs.utah.edu/ https://gentoo.osuosl.org/"
INPUT_DEVICES="synaptics libinput"
EOF
mkdir -p /mnt/gentoo/etc/portage/repos.conf
cp /mnt/gentoo/usr/share/portage/config/repos.conf /mnt/gentoo/usr/share/portage/config/repos.conf/gentoo.conf
cp -L /etc/resolv.conf /mnt/gentoo/etc/resolv.conf
mount -t proc proc /mnt/gentoo/proc
mount --rbind /sys /mnt/gentoo/sys
mount --rbind /dev /mnt/gentoo/dev
cat > /mnt/gentoo/install.sh <<EOF
set -ex
source /etc/profile
PS1="(chroot) \${PS1}"
export PS1
mkdir -p /boot
mount ${INSTALLDEV}1 /boot
emerge-webrsync
eselect profile set $PROFILE
emerge --verbose --update --deep --newuse @world
echo "$TIMEZONE" > /etc/timezone
emerge --config sys-libs/timezone-data
cat >/etc/locale.gen<<EOF2
en_US.UTF-8 UTF-8
C.UTF8 UTF-8
EOF2
locale-gen
eselect locale set $LOCALE
env-update
source /etc/profile
PS1="(chroot) \${PS1}"
export PS1

emerge sys-kernel/gentoo-sources sys-apps/pciutils app-arch/lzop app-arch/lz4
eselect kernel set \$(eselect kernel list | tail -n+2 | awk 'END{print\$2}')
cd /usr/src/linux
make oldconfig
make menuconfig
echo CONFIG_CMDLINE="net.ifnames=0" >> .config
make -j$(nproc)
make modules_install
make install

cat >>/etc/fstab<<EOF2
/dev/sda1 /boot vfat defaults,noatime 0 2
/dev/sda2 /   ext4    noatime 0 1
EOF2

cat | passwd <<EOF2
$PASSWORD
$PASSWORD
EOF2
USE='pam persist' emerge app-admin/doas
cat >/etc/doas.conf<<EOF2
permit keepenv persist ${USERNAME}
EOF2

emerge app-admin/sysklogd
rc-update add sysklogd default

cat >/etc/conf.d/hostname<<EOF2
hostname="$HOSTNAME"
EOF2
for ifname in $INTERFACES ; do
    ln -nfs /etc/init.d/net.lo /etc/init.d/net.${ifname}
    rc-update add net.${ifname} default
done

emerge net-misc/dhcpcd
rc-update add dhcpcd default
cat >/etc/dhcpcd.conf<<EOF2
clientid
persistent
vendorclassid
option domain_name_servers, domain_name, domain_search
option classless_static_routes
option interface_mtu
option rapid_commit
require dhcp_server_identifier
nohook resolv.conf
noipv4ll
noarp
noalias
noipv6
ipv4only
$(for ifname in $INTERFACES ; do
echo interface ${ifname}
echo  background
echo  timeout 10
done)
EOF2

emerge sys-boot/grub:2
grub-install --efi-directory=/boot --target=x86_64-efi --removable $INSTALLDEV
grub-mkconfig -o /boot/grub/grub.cfg
EOF
chroot /mnt/gentoo /bin/bash /install.sh | tee /mnt/gentoo/install.log
cd /
umount -R /mnt/gentoo
echo "Finished at $(date)"
