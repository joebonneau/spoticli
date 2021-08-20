import re

from click.types import Choice


class CommaSeparatedIndices(Choice):
    def convert(self, value, param, ctx):
        pattern = r"[^0-9, ]"
        search = re.search(pattern, value)
        if search is not None:
            self.fail("Input %s contains invalid characters" % value, param, ctx)
        choices = value.split(",")
        selection = []
        for choice in choices:
            if choice.strip() not in self.choices:
                self.fail(f"{choice.strip()} is an invalid index")
            else:
                selection.append(int(choice))
        return selection


class CommaSeparatedIndexRange(Choice):
    def convert(self, value, param, ctx):
        pattern = r"[^0-9, ]"
        search = re.search(pattern, value)
        if search is not None:
            self.fail("%s is not in the correct format." % value, param, ctx)
        choices = value.split(",")
        if len(choices) != 2:
            self.fail(
                "You may only enter a range containing two indices." % value, param, ctx
            )
        selection = []
        for choice in choices:
            if choice.strip() not in self.choices:
                self.fail(f"{choice.strip()} is an invalid index")
            else:
                selection.append(int(choice))
        return selection
