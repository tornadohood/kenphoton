# __Photon Overview__
This is where we'd put an overview of photon, but I'm lazy!  For a full description, please see the KB:
https://wiki.purestorage.com/pages/viewpage.action?pageId=46827128

# __Maintaince__
For issues with the photon library, please reach out to any of the following, or open a Jira
in the Support Tools (PT) project.  The current maintainers of photon are listed below.  Feel
free to reach out via slack to any of them, or email the team at support-dev@purestorage.com

## __Team Information__
Email:  support-dev@purestorage.com
Wiki:   https://wiki.purestorage.com/display/SDT/Support+Dev+Team

## __Maintainers__
* Aaron Muckleroy (aaronm@purestorage.com)
* Jacob Hopkinson (jhop@purestorage.com)
* Micheal Taylor  (bub@purestorage.com)
* Rich Stacey     (richstacey@purestorage.com)

# __Conventions__
General convention sections are listed below.  These are conventions for things like documentation,
code quality expectations,

## __Code Notations__
### __Jiras__
#### __Conventions for JIRA notations__
There are often times when we need to reference a jira for specific logic choices so that folks know
we chose this over other options.  This is different than a #CAVEAT in that a # CAVEAT is a one off
that we need to account for.  # JIRA is more appropriate for something like in ddump_utils where we
match specific loglines to specific pathologies.  The easy rule of thumb is that if you want someone
to know why you're adding code so that they can research the choice, you can put the jira number.

Jira notations should be on a single line.

#### __Jira Examples__

### __Caveats__
#### __Conventions for caveats__

In photon, we've found a lot of "gotchas" just like previous engineers did with how finicky logs may
need to be parsed, or odd behaviors that we need to account for that aren't intuitive until we had
to solve the problem.  For these types of scenarios, we have comments noted as a # CAVEAT.

1. Caveats will not be inline comments
2. Caveats will begin with # CAVEAT: <brief_description>
3. Caveats will have a brief description that is one line
4. Caveats will have longer descriptions in an uninterrupted code block.

#### __Caveat Examples__

Single Line:
    # CAVEAT: Sometimes we won't get

Multi Line:
    # CAVEAT: Get from <date> 00:00:00 to <date> 23:59:59.999999.
    # We want to have a timestamp that's before midnight, but after any
    # possible granularity of time that would be between a timstamp and midnight
    # otherwise we risk losing data at that edge case.


