function Component() {}
Component.prototype.createOperations = function() {
    component.createOperations();
    var baseDir  = "@TargetDir@";
    var trayExe  = baseDir + "\\xopat_tray_binary\\xopat_tray_binary.exe";
    var iconFile = baseDir + "\\xopat_tray_binary\\_internal\\xopat-logo.ico";
    component.addOperation(
        "CreateShortcut",
        trayExe,
        "@StartMenuDir@\\xOpat\\xOpat.lnk",
        "workingDirectory=" + baseDir,
        "iconPath=" + iconFile
    );
    component.addOperation(
        "CreateShortcut",
        trayExe,
        "@DesktopDir@\\xOpat.lnk",
        "workingDirectory=" + baseDir,
        "iconPath=" + iconFile
    );
};