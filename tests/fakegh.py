"""An in-memory GitHub that answers the gh commands Shipit sends."""
import json


class FakeGitHub:
    def __init__(self, issues=(), labels=("bug",), milestones=(), fail_on=None):
        self.issues = {i["number"]: {"state": "open", "body": "", "assignees": [], "labels": [],
                                     "comments": [], **i} for i in issues}
        self.labels, self.milestones = set(labels), set(milestones)
        self.calls, self.fail_on = [], fail_on

    def __call__(self, args, input=None, **_):
        assert args[0] == "gh"
        self.calls.append(args[1:])
        if self.fail_on and self.fail_on in args:
            return 1, "", "HTTP 502: Bad gateway"
        a = args[1:]
        if a[:2] == ["issue", "list"]:
            return 0, json.dumps(self.list(a)), ""
        if a[:2] == ["label", "list"]:
            return 0, json.dumps([{"name": n} for n in self.labels]), ""
        if a[:2] == ["label", "create"]:
            self.labels.add(a[2])
        elif a[0] == "api" and "POST" in a:
            self.milestones.add(a[a.index("-f") + 1].split("=", 1)[1])
        elif a[0] == "api":
            return 0, json.dumps([{"title": t} for t in self.milestones]), ""
        elif a[:2] == ["issue", "create"]:
            n = max(self.issues, default=0) + 1
            self.issues[n] = {"number": n, "title": opt(a, "--title"), "body": input, "state": "open",
                              "labels": all_opts(a, "--label"), "assignees": all_opts(a, "--assignee"),
                              "milestone": opt(a, "--milestone"), "comments": []}
            return 0, f"https://github.com/o/r/issues/{n}\n", ""
        elif a[:2] == ["issue", "view"]:
            return 0, json.dumps({"body": self.issues[int(a[2])]["body"]}), ""
        elif a[:2] == ["issue", "edit"]:
            issue = self.issues[int(a[2])]
            if "--body-file" in a:
                issue["body"] = input
            issue["assignees"] = [x for x in issue["assignees"] if x not in all_opts(a, "--remove-assignee")]
            issue["assignees"] += all_opts(a, "--add-assignee")
        elif a[:2] == ["issue", "comment"]:
            self.issues[int(a[2])]["comments"].append(input)
        elif a[:2] == ["issue", "close"]:
            issue = self.issues[int(a[2])]
            issue["state"] = "closed"
            issue["comments"].append(opt(a, "--comment"))
        return 0, "", ""

    def list(self, a):
        state = opt(a, "--state")
        rows = [i for i in self.issues.values() if state == "all" or i["state"] == state]
        search = opt(a, "--search")
        if search:
            rows = [i for i in rows if search.split('"')[1].lower() in i["title"].lower()]
        return [{"number": i["number"], "title": i["title"],
                 "assignees": [{"login": x} for x in i["assignees"]],
                 "labels": [{"name": x} for x in i["labels"]]} for i in rows]


def opt(args, name):
    return args[args.index(name) + 1] if name in args else None


def all_opts(args, name):
    return [args[i + 1] for i, a in enumerate(args) if a == name]
