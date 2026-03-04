function Component() {}
Component.prototype.createOperations = function() {
    component.createOperations();
    var baseDir      = "@TargetDir@";
    var launcherVbs  = baseDir + "\\start_all.vbs";
    var xopatExe     = baseDir + "\\xopat\\xopat_binary.exe";
    component.addOperation(
        "CreateShortcut",
        launcherVbs,
        "@StartMenuDir@\\xOpat\\xOpat.lnk",
        "workingDirectory=" + baseDir,
        "iconPath=" + xopatExe
    );
    component.addOperation(
        "CreateShortcut",
        launcherVbs,
        "@DesktopDir@\\xOpat.lnk",
        "workingDirectory=" + baseDir,
        "iconPath=" + xopatExe
    );
};