import re

from click.types import Choice, ParamType


class CommaSeparatedIndices(Choice):
    """
    Extends the click.Choice type class to add built-in handling for the input of comma-separated
    indices. Accepts input as <int, int, ...>.
    """

    def convert(self, value, param, ctx):
        # Use regex to confirm only numbers and commas were provided
        pattern = r"[^0-9, ]"
        search = re.search(pattern, value)
        # Fail the input if invalid characters were found
        if search is not None:
            self.fail("Input %s contains invalid characters" % value, param, ctx)
        choices = value.split(",")
        selection = []
        for choice in choices:
            if choice.strip() not in self.choices:
                self.fail(f"{choice.strip()} is an invalid index")
            else:
                # Return the inputs as integers for convenience
                selection.append(int(choice))
        return selection


class CommaSeparatedIndexRange(Choice):
    """
    Extends the click.Choice class to add built-in handling for the input of comma-separated index
    ranges.
    """

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


class SpotifyCredential(ParamType):
    """
    Validates that the input is both 32 characters long and contains only alphanumeric
    characters.
    """

    def convert(self, value, param, ctx):
        # Use regex to confirm only numbers and commas were provided
        if len(value) != 32:
            self.fail("Input must be 32 characters long")
        pattern = r"\w{32}"
        search = re.search(pattern, value)
        # Fail the input if invalid characters were found
        if search is None:
            self.fail("Input contains invalid characters")

        return search.group()
