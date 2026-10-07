"""Every GitHub call goes through Gh, so --dry-run and test mocks share one seam.

Reads always run. Writes run for real, or are printed when dry_run is on.
Bodies go through stdin (--body-file -) so quotes and Hinglish survive intact.
"""
import json
import re
import subprocess

from . import proc
from .console import say


class GhError(Exception):
    pass


class Gh:
    def __init__(self, slug, dry_run=False, run=proc.run, echo=say):
        self.slug, self.dry, self.run, self.echo = slug, dry_run, run, echo
        self.fake = 0

    def call(self, args, input=None, write=False):
        if write and self.dry:
            note = f"   <<< body: {input.splitlines()[-1][:60]}" if input else ""
            self.echo("  $ " + subprocess.list2cmdline(["gh", *args]) + note)
            return ""
        code, out, err = self.run(["gh", *args], input=input)
        if code:
            lines = (err or "").strip().splitlines()
            raise GhError(lines[-1] if lines else f"gh {args[0]} failed")
        return out

    def json(self, args):
        return json.loads(self.call(args) or "null")

    # Reads
    def open_issues(self):
        return self.json(["issue", "list", "-R", self.slug, "--state", "open", "--limit", "500",
                          "--json", "number,title,assignees,labels"])

    def find_issue(self, title):
        found = self.json(["issue", "list", "-R", self.slug, "--state", "all", "--search",
                           f'"{title}" in:title', "--json", "number,title"])
        return next((i["number"] for i in found if i["title"] == title), None)

    def labels(self):
        return {l["name"] for l in self.json(["label", "list", "-R", self.slug, "--limit", "200",
                                              "--json", "name"])}

    def milestones(self):
        return {m["title"] for m in self.json(["api", f"repos/{self.slug}/milestones?state=all"
                                                      "&per_page=100"])}

    def body(self, number):
        return self.json(["issue", "view", str(number), "-R", self.slug, "--json", "body"])["body"]

    # Writes
    def create_label(self, name, color, description):
        self.call(["label", "create", name, "-R", self.slug, "--color", color,
                   "--description", description, "--force"], write=True)

    def create_milestone(self, title, due):
        self.call(["api", "-X", "POST", f"repos/{self.slug}/milestones", "-f", f"title={title}",
                   "-f", f"due_on={due}T23:59:59Z"], write=True)

    def create_issue(self, title, body, labels=(), assignee=None, milestone=None):
        args = ["issue", "create", "-R", self.slug, "--title", title, "--body-file", "-"]
        for label in labels:
            args += ["--label", label]
        if assignee:
            args += ["--assignee", assignee]
        if milestone:
            args += ["--milestone", milestone]
        out = self.call(args, input=body, write=True)
        if self.dry:
            self.fake += 1
            return f"new{self.fake}"
        m = re.search(r"/issues/(\d+)", out)
        if not m:
            raise GhError("gh didn't return an issue URL")
        return int(m.group(1))

    def edit_body(self, number, body):
        self.call(["issue", "edit", str(number), "-R", self.slug, "--body-file", "-"],
                  input=body, write=True)

    def comment(self, number, body):
        self.call(["issue", "comment", str(number), "-R", self.slug, "--body-file", "-"],
                  input=body, write=True)

    def close(self, number, comment):
        self.call(["issue", "close", str(number), "-R", self.slug, "--comment", comment],
                  write=True)

    def reassign(self, number, to, old=None):
        args = ["issue", "edit", str(number), "-R", self.slug, "--add-assignee", to]
        if old and old != to:
            args += ["--remove-assignee", old]
        self.call(args, write=True)

    def url(self, number):
        return f"https://github.com/{self.slug}/issues/{number}"
