import sublime_plugin
import os
from subprocess import Popen, PIPE
from tempfile import SpooledTemporaryFile as tempfile
import json


class RequireNodeCommand(sublime_plugin.TextCommand):
    def write_require(self, resolvers, edit):
        def write(index):
            if index == -1:
                return
            [module_candidate_name, module_rel_path] = resolvers[index]()
            require_directive = "%s = require(\"%s\")" % (module_candidate_name, module_rel_path)
            region = self.view.sel()[0]
            # self.view.sel().clear()
            self.view.insert(edit, region.a, require_directive)
            # self.view.sel().add(sublime.Region(region.a, region.a + len(module_candidate_name)))

        return write

    def resolve_from_file(self, full_path):
        def resolve():
            file = self.view.file_name()
            file_wo_ext = os.path.splitext(full_path)[0]
            module_candidate_name = os.path.basename(file_wo_ext).replace(".", "")
            module_rel_path = os.path.relpath(file_wo_ext, os.path.dirname(file))

            if module_rel_path[:3] != "../":
                module_rel_path = "./" + module_rel_path

            return [module_candidate_name, module_rel_path]
        return resolve

    def get_suggestion_from_nodemodules(self):
        resolvers = []
        suggestions = []
        current_file_dirs = self.view.file_name().split(os.path.sep)
        current_dir = os.path.split(self.view.file_name())[0]
        for x in range(len(self.view.window().folders()[0].split(os.path.sep)), len(current_file_dirs))[::-1]:
            candidate = os.path.join(current_dir, "node_modules")
            if os.path.exists(candidate):
                for dir in [name for name in os.listdir(candidate)
                                 if os.path.isdir(os.path.join(candidate, name))]:
                    resolvers.append(lambda dir=dir: [dir, dir])
                    suggestions.append("module: " + dir)
                break
            current_dir = os.path.split(current_dir)[0]
        return [resolvers, suggestions]

    def get_suggestion_native_modules(self):
        try:
            f = tempfile()
            f.write('console.log(Object.keys(process.binding("natives")))')
            f.seek(0)
            jsresult = (Popen(['node'], stdout=PIPE, stdin=f)).stdout.read().replace("'", '"')
            f.close()

            results = json.loads(jsresult)

            result = [[(lambda ni=ni: [ni, ni]) for ni in results],
                    ["native: " + ni for ni in results]]
            return result
        except Exception:
            return [[], []]

    def run(self, edit):
        folder = self.view.window().folders()[0]
        suggestions = []
        resolvers = []

        #create suggestions for all files in the project
        for root, subFolders, files in os.walk(folder, followlinks=True):
            for file in files:
                resolvers.append(self.resolve_from_file(os.path.join(root, file)))
                suggestions.append([file, root.replace(folder, "", 1) or file])

        #create suggestions for modules in node_module folder
        [resolvers_from_nm, suggestions_from_nm] = self.get_suggestion_from_nodemodules()
        resolvers += resolvers_from_nm
        suggestions += suggestions_from_nm

        #create suggestions from native modules
        [resolvers_from_native, suggestions_from_nm] = self.get_suggestion_native_modules()
        resolvers += resolvers_from_native
        suggestions += suggestions_from_nm

        self.view.window().show_quick_panel(suggestions, self.write_require(resolvers, edit))
