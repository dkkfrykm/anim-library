# Pack phase-5 clip modules (+ base style modules) into one rbxmx Folder for drag-in install.
import sys, os, glob
D = sys.argv[1]; out = sys.argv[2]; name = os.path.splitext(os.path.basename(out))[0]
files = sorted(glob.glob(os.path.join(D, "Clips_Sky*.lua"))) + sorted(glob.glob(os.path.join(D, "base", "Clips_Sky*.lua")))
x = ['<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">',
     '<Item class="Folder" referent="RBX0"><Properties><string name="Name">%s</string></Properties>' % name]
for k, f in enumerate(files, 1):
    src = open(f, encoding="utf-8").read().replace("\r\n", "\n").replace("]]>", "]]]]><![CDATA[>")
    x.append('<Item class="ModuleScript" referent="RBX%d"><Properties><string name="Name">%s</string><ProtectedString name="Source"><![CDATA[%s]]></ProtectedString></Properties></Item>'
             % (k, os.path.splitext(os.path.basename(f))[0], src))
x.append("</Item></roblox>")
open(out, "w", encoding="utf-8", newline="\n").write("\n".join(x))
print(len(files), "modules ->", out, os.path.getsize(out))
