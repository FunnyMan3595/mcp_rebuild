#!/bin/bash -v
# Clear out old files.
rm src/minecraft/*.java
# Install Buildcraft API
cp -r fm/bc3/net/minecraft/src/buildcraft src/minecraft/net/minecraft/src || exit
# Install mod source.
cp fm/*/*.java src/minecraft/ || exit
# Recompile
./recompile.sh || exit
# Install IC2 (full).
cp -r ic2-unz/net bin/minecraft/ || exit
# Reobfuscate
./reobfuscate.sh || exit
# Pack class files into jars.
cd reobf/minecraft/ || exit
jar -cvf ~/../samba_root/DebugCrop.jar mod_DebugCrop.class DebugCrop.class || exit
jar -cvf ~/../samba_root/HelperCrops.jar mod_HelperCrops.class SoybeanCrop.class WaterrootCrop.class || exit
jar -cvf ~/../samba_root/ExperiMint.jar mod_ExperiMint.class ExperiMint.class || exit
jar -cvf ~/../samba_root/SeedManager.jar mod_SeedManager.class SeedManager*.class SeedLibrary*.class SeedAnalyzer*.class VerboseItemCropSeed.class buildcraft/api/{Orientations,ISpecialInventory}.class || exit
# Pack source and resources into jars.
cd ../../fm/ || exit
jar -uvf ~/../samba_root/HelperCrops.jar fm_crops.png || exit
jar -uvf ~/../samba_root/ExperiMint.jar fm_crops.png || exit
cd DebugCrop/ || exit
jar -uvf ~/../samba_root/DebugCrop.jar * || exit
cd ../HelperCrops/ || exit
jar -uvf ~/../samba_root/HelperCrops.jar * || exit
cd ../ExperiMint/ || exit
jar -uvf ~/../samba_root/ExperiMint.jar * || exit
cd ../SeedManager/ || exit
jar -uvf ~/../samba_root/SeedManager.jar * || exit
# Success!
