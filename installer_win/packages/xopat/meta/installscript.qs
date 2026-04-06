function Component() {}
Component.prototype.createOperations = function() {
    component.createOperations();
    var baseDir  = "@TargetDir@";
    var trayExe  = baseDir + "\\xopat_tray_binary\\xopat_tray_binary.exe";
    component.addOperation(
        "CreateShortcut",
        trayExe,
        "@StartMenuDir@\\xOpat\\xOpat.lnk",
        "workingDirectory=" + baseDir,
        "iconPath=" + trayExe
    );
    component.addOperation(
        "CreateShortcut",
        trayExe,
        "@DesktopDir@\\xOpat.lnk",
        "workingDirectory=" + baseDir,
        "iconPath=" + trayExe
    );
};