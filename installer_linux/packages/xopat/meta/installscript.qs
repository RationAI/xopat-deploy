function Component() {}
Component.prototype.createOperations = function() {
    component.createOperations();
    component.addOperation("Execute", "chmod", "+x", "@TargetDir@/wsi-service/wsi_service_binary");
    component.addOperation("Execute", "chmod", "+x", "@TargetDir@/xopat/xopat_binary");
    component.addOperation("Execute", "chmod", "+x", "@TargetDir@/start_all.sh");
    component.addOperation(
        "CreateDesktopEntry",
        "@HomeDir@/.local/share/applications/xOpat.desktop",
        "Type=Application\nName=xOpat\nExec=@TargetDir@/start_all.sh\nTerminal=false\nCategories=Science;"
    );
};