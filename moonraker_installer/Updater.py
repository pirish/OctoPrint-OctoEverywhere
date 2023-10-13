import os
import stat

from moonraker_octoeverywhere.version import Version

from .Context import Context
from .Logging import Logger
from .Configure import Configure
from .Util import Util

#
# This class is responsible for doing updates for all plugins and companions on this local system.
# This update logic is mostly for companion plugins, since normal plugins will be updated via the moonraker update system.
# But it does work for both.
#
# However, this is quite easy, for a few reasons.
#    1) All plugins and companions will use the same ~/octoeverywhere/ git repo.
#    2) We always run the ./install.sh script before launching the PY installer, which handles updating system packages and PIP packages.
#
# So all we really need to do is find and restart all of the services.
#
class Updater:

    def DoUpdate(self, context:Context):
        Logger.Header("Starting Update Logic")
        # Enumerate all service file to find any local plugins and companion service files.
        # Use sorted, so the results are in a nice user presentable order.
        foundOeServices = []
        fileAndDirList = sorted(os.listdir(Util.SystemdServiceFilePath))
        for fileOrDirName in fileAndDirList:
            Logger.Debug(f" Searching for OE services to update, found: {fileOrDirName}")
            if fileOrDirName.lower().startswith(Configure.c_ServiceCommonNamePrefix):
                foundOeServices.append(fileOrDirName)

        if len(foundOeServices) == 0:
            Logger.Warn("No local plugins or companions were found.")
            raise Exception("No local plugins or companions were found.")

        Logger.Info("We found the following plugins to update:")
        for s in foundOeServices:
            Logger.Info(f"  {s}")

        Logger.Info("Restarting services...")

        for s in foundOeServices:
            (returnCode, output) = Util.RunShellCommand("systemctl restart "+s)
            if returnCode != 0:
                Logger.Warn(f"Service {s} might have failed to restart. Output: {output}")

        pluginVersionStr = "Unknown"
        try:
            pluginVersionStr = Version.GetPluginVersion(context.RepoRootFolder)
        except Exception as e:
            Logger.Warn("Failed to parse setup.py for plugin version. "+str(e))


        Logger.Blank()
        Logger.Header("-------------------------------------------")
        Logger.Info(  "    OctoEverywhere Update Successful")
        Logger.Info( f"       New Version: {pluginVersionStr}")
        Logger.Purple("            Happy Printing!")
        Logger.Header("-------------------------------------------")
        Logger.Blank()


    # This function ensures there's an update script placed in the user's root directory, so it's easy for the user to find
    # the script for updating.
    def PlaceUpdateScriptInRoot(self, context:Context) -> bool:
        try:
            # Create the script file with any optional args we might need.
            s = f'''\
#!/bin/bash

#
# This script will update all of the OctoEverywhere for Klipper instances on this device!
#
# This works for both the normal plugin install (where Klipper is running on this device) and Companion plugins.
#
# If you need help, feel free to contact us at support@octoeverywhere.com
#

# The update and install scripts need to be ran from the repo root.
# So just cd and execute our update script! Easy peasy!
startingDir=$(pwd)
cd {context.RepoRootFolder}
./update.sh
cd $startingDir
            '''
            updateFilePath = os.path.join(context.UserHomePath, "update-octoeverywhere.sh")
            with open(updateFilePath, 'w', encoding="utf-8") as f:
                f.write(s)
            # Make sure to make it executable
            st = os.stat(updateFilePath)
            os.chmod(updateFilePath, st.st_mode | stat.S_IEXEC)
            return True
        except Exception as e:
            Logger.Error("Failed to write updater script to user home. "+str(e))
            return False