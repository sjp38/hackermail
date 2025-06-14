#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import copy
import datetime
import json
import math
import os
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

import _hkml
import _hkml_list_cache
import hkml_cache
import hkml_common
import hkml_fetch
import hkml_open
import hkml_patch
import hkml_tag
import hkml_view
import hkml_view_mails


def args_to_lists_cache_key(args):
    dict_ = copy.deepcopy(args.__dict__)
    dict_["cols"] = None
    dict_["fetch"] = False
    dict_["stdout"] = False
    dict_["dim_old"] = None
    dict_["read_dates"] = False

    keys = list(dict_.keys())
    # remove keys that not really affect resulting list.
    for k in keys:
        if not k in {
            "hkml_dir",
            "directory",
            "command",
            "manifest",
            "sources",
            "source_type",
            "since",
            "until",
            "nr_mails",
            "min_nr_mails",
            "max_nr_mails",
            "do_find_ancestors_from_cache",
            "pisearch",
            "stat_only",
            "stat_authors",
            "from_keywords",
            "from_to_keywords",
            "from_to_cc_keywords",
            "subject_keywords",
            "body_keywords",
            "new",
            "collapse",
            "sort_threads_by",
            "ascend",
            "hot",
            "cols",
            "url",
            "hide_stat",
            "runtime_profile",
            "max_len_list",
            "dim_old",
            "fetch",
            "ignore_cache",
            "stdout",
            "use_less",
            "read_dates",
            "keywords_for",
            "patches_for",
            "keywords",
        }:
            del dict_[k]

    # --keywords_for was introduced after v1.3.8, with default value 'each'
    if dict_["keywords_for"] == "each":
        del dict_["keywords_for"]
    # --patches_for was introduced after v1.3.8, with default value None
    if dict_["patches_for"] is None:
        del dict_["patches_for"]
    # --keywords was introduced after v1.3.8, with default value None
    if dict_["keywords"] is None:
        del dict_["keywords"]

    return json.dumps(dict_, sort_keys=True)


def map_idx_to_mail_cache_key(mail, mail_idx_key_map):
    idx = mail.pridx
    key = hkml_cache.get_cache_key(
        mail.gitid, mail.gitdir, mail.get_field("message-id")
    )

    idx_str = "%d" % idx
    if idx_str in mail_idx_key_map:
        return
    mail_idx_key_map[idx_str] = key


class MailListDecorator:
    collapse = None
    sort_threads_by = None
    ascend = None
    cols = None
    show_url = None
    hide_stat = None
    runtime_profile = None
    max_len = None

    def __init__(self, args):
        if args is None:
            return

        self.collapse = args.collapse
        self.sort_threads_by = args.sort_threads_by
        self.ascend = args.ascend
        self.cols = args.cols
        self.show_url = args.url
        self.hide_stat = args.hide_stat
        self.runtime_profile = args.runtime_profile
        self.max_len = args.max_len_list

        if args.hot:
            self.ascend = False
            self.sort_threads_by = ["last_date", "nr_comments"]
            self.collapse = True

    def to_kvpairs(self):
        kvpairs = copy.deepcopy(vars(self))
        return {k: v for k, v in kvpairs.items() if v is not None}

    @classmethod
    def from_kvpairs(cls, kvpairs):
        self = cls(None)
        for key, value in kvpairs.items():
            setattr(self, key, value)
        return self


def wrap_line(prefix, line, nr_cols):
    """Wrap a string for a limited columns and returns a list of resulting
    lines.  Second and below lines starts with spaces of 'prefix' length.
    For example:
    >>> print('\n'.join(hkml_list.wrap_line('[something]', 'foo bar baz asdf', 20)))
    [something] foo bar
                baz asdf
    """
    lines = []
    words = [prefix] + line.split(" ")
    words_to_print = []
    for w in words:
        words_to_print.append(w)
        line_len = len(" ".join(words_to_print))
        if nr_cols is not None and line_len > nr_cols:
            if len(words_to_print) == 1:
                lines.append(words_to_print[0])
            else:
                lines.append(" ".join(words_to_print[:-1]))
                words_to_print = [" " * (len(prefix) + 1) + words_to_print[-1]]
    lines.append(" ".join(words_to_print))
    return lines


def find_ancestors_from_cache(mail, by_msgids, found_parents):
    parent_msgid = mail.get_field("in-reply-to-msgid")
    if parent_msgid is None or parent_msgid in by_msgids:
        return
    parent = hkml_cache.get_mail(key=parent_msgid)
    if parent is None:
        return
    by_msgids[parent.get_field("message-id")] = parent
    found_parents.append(parent)
    if parent.get_field("in-reply-to") is None:
        return
    find_ancestors_from_cache(parent, by_msgids, found_parents)


def threads_of(mails, do_find_ancestors_from_cache=False):
    by_msgids = {}
    for mail in mails:
        msgid = mail.get_field("message-id")
        if msgid is None:
            continue
        by_msgids[mail.get_field("message-id")] = mail

    if do_find_ancestors_from_cache:
        found_parents = []
        for mail in mails:
            find_ancestors_from_cache(mail, by_msgids, found_parents)
        mails += found_parents

    threads = []
    for mail in mails:
        in_reply_to = mail.get_field("in-reply-to-msgid")
        if not in_reply_to in by_msgids:
            threads.append(mail)
        else:
            orig_mail = by_msgids[in_reply_to]
            if not mail in orig_mail.replies:
                orig_mail.replies.append(mail)
            mail.parent_mail = orig_mail
    return threads


def orig_subject_formatted(mail):
    if mail.parent_mail is None:
        return False
    if mail.parent_mail.filtered_out == False:
        return True
    return orig_subject_formatted(mail.parent_mail)


def format_entry(mail, max_digits_for_idx, show_nr_replies, show_url, nr_cols):
    index = "%d" % mail.pridx
    nr_zeroes = max_digits_for_idx - len(index)
    index = "%s%s" % ("0" * nr_zeroes, index)
    prefix = "[%s]%s" % (index, " " * 2 * mail.prdepth)

    subject = "%s" % mail.get_field("subject")
    if mail.prdepth and subject.lower().startswith("re: "):
        subject = subject[4:]
        if orig_subject_formatted(mail):
            parent_subject = mail.parent_mail.get_field("subject")
            if parent_subject[:4].lower() == "re: ":
                parent_subject = parent_subject[4:]
            if parent_subject == subject:
                subject = "re:"

    from_fields = mail.get_field("from").split()
    if len(from_fields) > 1:
        from_fields = from_fields[0:-1]
    suffices = [" ".join(from_fields), mail.date.strftime("%Y/%m/%d %H:%M")]
    if show_nr_replies:
        suffices.append("%d+ msgs" % nr_replies_of(mail))
    if show_url:
        suffices.append(mail.url())
    suffix = " (%s)" % ", ".join(suffices)

    lines = wrap_line(prefix, subject + suffix, nr_cols)
    return lines


def nr_replies_of(mail):
    nr = len(mail.replies)
    for re in mail.replies:
        nr += nr_replies_of(re)
    return nr


def root_of_thread(mail):
    if mail.parent_mail is None:
        return mail
    return root_of_thread(mail.parent_mail)


def set_index(mail, list_, depth, mail_idx_key_map):
    """Make mails to be all ready for print in list"""
    mail.pridx = len(list_)
    mail.prdepth = depth
    list_.append(mail)

    map_idx_to_mail_cache_key(mail, mail_idx_key_map)

    for mail in mail.replies:
        set_index(mail, list_, depth + 1, mail_idx_key_map)


def last_reply_date(mail, prev_last_date):
    if len(mail.replies) == 0:
        if prev_last_date == None or prev_last_date < mail.date:
            return mail.date
        return prev_last_date

    for reply in mail.replies:
        prev_last_date = last_reply_date(reply, prev_last_date)
    return prev_last_date


def nr_comments(mail):
    nr_comments = nr_replies_of(mail)
    # Exclude replies that sent together as a patch series
    if not mail.get_field("in-reply-to") and mail.series is not None:
        nr_comments -= mail.series[1]
    return nr_comments


def sort_threads(threads, category):
    if category == "first_date":
        return
    if category == "last_date":
        threads.sort(key=lambda t: last_reply_date(t, None))
    elif category == "nr_replies":
        threads.sort(key=lambda t: nr_replies_of(t))
    elif category == "nr_comments":
        threads.sort(key=lambda t: nr_comments(t))


def all_keywords_in(keywords, text):
    if keywords is None:
        return True
    for keyword in keywords:
        if keyword is not None and not keyword in text:
            return False
    return True


def keywords_in(keywords, text):
    if keywords is None:
        return True
    for sub_keywords in keywords:
        if all_keywords_in(sub_keywords, text):
            return True
    return False


class MailListFilter:
    new_threads_only = None
    from_keywords = None
    from_to_keywords = None
    from_to_cc_keywords = None
    subject_keywords = None
    body_keywords = None
    keywords_for = None
    patches_for = None

    def __init__(self, args):
        if args is None:
            return
        self.new_threads_only = args.new
        self.from_keywords = args.from_keywords
        self.from_to_keywords = args.from_to_keywords
        self.from_to_cc_keywords = args.from_to_cc_keywords
        self.subject_keywords = args.subject_keywords
        self.body_keywords = args.body_keywords
        self.keywords_for = args.keywords_for
        self.patches_for = args.patches_for
        if args.keywords is not None:
            for keywords in args.keywords:
                field = keywords[0]
                filter_keywords = keywords[1:]
                if field == "from":
                    if self.from_keywords is None:
                        self.from_keywords = []
                    self.from_keywords.append(filter_keywords)
                if field == "from_to":
                    if self.from_to_keywords is None:
                        self.from_to_keywords = []
                    self.from_keywords.append(filter_keywords)
                if field == "from_to_cc":
                    if self.from_to_cc_keywords is None:
                        self.from_to_cc_keywords = []
                    self.from_keywords.append(filter_keywords)
                if field == "subject":
                    if self.subject_keywords is None:
                        self.subject_keywords = []
                    self.from_keywords.append(filter_keywords)
                if field == "body":
                    if self.body_keywords is None:
                        self.body_keywords = []
                    self.from_keywords.append(filter_keywords)

    def no_filter_set(self):
        return (
            not self.new_threads_only
            and not self.from_keywords
            and not self.from_to_keywords
            and not self.from_to_cc_keywords
            and not self.subject_keywords
            and not self.body_keywords
            and not self.patches_for
        )

    def thread_mails_from(self, mail, mails):
        mails.append(mail)
        for reply in mail.replies:
            self.thread_mails_from(reply, mails)

    def mails_to_check_keywords(self, mail):
        if self.keywords_for == "each":
            return [mail]
        elif self.keywords_for == "root":
            while mail.parent_mail is not None:
                mail = mail.parent_mail
            return [mail]
        elif self.keywords_for == "thread":
            while mail.parent_mail is not None:
                mail = mail.parent_mail
            mails = []
            self.thread_mails_from(mail, mails)
            return mails

    def should_filter_out_keywords_one(self, mail):
        if not keywords_in(self.from_keywords, mail.get_field("from")):
            return True
        if not keywords_in(
            self.from_to_keywords,
            "%s %s" % (mail.get_field("from"), mail.get_field("to")),
        ):
            return True
        if not keywords_in(
            self.from_to_cc_keywords,
            "%s %s %s"
            % (mail.get_field("from"), mail.get_field("to"), mail.get_field("cc")),
        ):
            return True
        if not keywords_in(self.subject_keywords, mail.subject):
            return True
        if not keywords_in(self.body_keywords, mail.get_field("body")):
            return True
        return False

    def should_filter_out_keywords(self, mails):
        # if any mail is ok to filter in, filter in.
        if mails is None:
            return True
        for mail in mails:
            if not self.should_filter_out_keywords_one(mail):
                return False
        return True

    def should_filter_out_patches(self, mail):
        if self.patches_for is None:
            return False
        if not "patch" in mail.subject_tags:
            return True
        if self.patches_for in [["review"], ["pick"]]:
            if hkml_patch.is_cover_letter(mail):
                return True
            reviewed, err = hkml_view_mails.is_reviewed(mail)
            if err is not None:
                return False
            filter_out_reviewed = self.patches_for == ["review"]
            return reviewed is not filter_out_reviewed
        if self.patches_for[0] == "reviewer":
            if not os.path.isfile("MAINTAINERS"):
                print("MAINTAINERS file not found!!")
                return False
            with open("MAINTAINERS", "r") as f:
                maintainers_file_content = f.read()
            reviewer = " ".join(self.patches_for[1:])
            files_for_reviewer = hkml_view_mails.get_files_for_reviewer(
                reviewer, maintainers_file_content
            )
            if not "patch" in mail.subject_tags:
                return True
            if hkml_patch.is_cover_letter(mail):
                return True
            if not hkml_view_mails.patch_is_touching(mail, files_for_reviewer):
                return True
        return False

    def should_filter_out(self, mail):
        if self.no_filter_set():
            return False

        if self.new_threads_only and mail.get_field("in-reply-to"):
            return True

        if self.should_filter_out_keywords(self.mails_to_check_keywords(mail)):
            return True

        if self.should_filter_out_patches(mail):
            return True

        return False

    def to_kvpairs(self):
        kvpairs = copy.deepcopy(vars(self))
        return {k: v for k, v in kvpairs.items() if v is not None}

    @classmethod
    def from_kvpairs(cls, kvpairs):
        self = cls(None)
        for key, value in kvpairs.items():
            """
            _filter command line options was not having action='append' argument
            before.  Handle the type compatibility from old version-generated
            kvpairs.
            """
            if key in [
                "from_keywords",
                "from_to_keywords",
                "from_to_cc_keywords",
                "subject_keywords",
                "body_keywords",
            ]:
                if type(value) is list and len(value) > 0:
                    if type(value[0]) is not list:
                        value = [value]
            setattr(self, key, value)
        return self


def format_stat(mails_to_show, stat_authors):
    nr_threads = 0
    nr_new_threads = 0
    nr_patches = 0
    nr_patchsets = 0
    oldest = None
    latest = None
    authors_nr_mails = {}
    for mail in mails_to_show:
        if mail.parent_mail is None:
            nr_threads += 1
        if not mail.get_field("in-reply-to"):
            nr_new_threads += 1
        if "patch" in mail.subject_tags:
            nr_patches += 1
        if "patch" in mail.subject_tags and not mail.get_field("in-reply-to"):
            nr_patchsets += 1
        if oldest is None or mail.date < oldest.date:
            oldest = mail
        if latest is None or latest.date < mail.date:
            latest = mail
        author = mail.get_field("from")
        if not author in authors_nr_mails:
            authors_nr_mails[author] = 0
        authors_nr_mails[author] += 1

    lines = []
    lines.append(
        "# %d mails, %d threads, %d new threads"
        % (len(mails_to_show), nr_threads, nr_new_threads)
    )
    lines.append("# %d patches, %d series" % (nr_patches, nr_patchsets))
    if oldest is not None:
        lines.append("# oldest: %s" % oldest.date)
        lines.append("# newest: %s" % latest.date)
    if stat_authors:
        authors = [
            [x, authors_nr_mails[x]]
            for x in sorted(
                authors_nr_mails.keys(), reverse=True, key=lambda x: authors_nr_mails[x]
            )[:10]
        ]
        lines.append("# top %d authors" % len(authors))
        for author, nr_mails in authors:
            lines.append("# - %s: %d" % (author, nr_mails))
    return lines


def get_filtered_mails(mails, ls_range, mails_filter):
    filtered_mails = []
    for mail in mails:
        if ls_range is not None and not mail.pridx in ls_range:
            mail.filtered_out = True
            continue
        if mails_filter is not None and mails_filter.should_filter_out(mail):
            mail.filtered_out = True
            continue
        mail.filtered_out = False
        filtered_mails.append(mail)
    return filtered_mails


class RuntimeProfile:
    start_time = None
    end_time = None
    runtime = None

    def __init__(self):
        self.start_time = time.time()

    def done(self):
        self.end_time = time.time()
        self.runtime = self.end_time - self.start_time


class RuntimeProfiles:
    profiles = None  # category name to RuntimeProfile dict
    print_progress = None

    def __init__(self, print_progress):
        self.profiles = {}
        self.print_progress = print_progress

    def start(self, category):
        self.profiles[category] = RuntimeProfile()
        if self.print_progress:
            print("# %s start" % category)

    def end(self, category):
        self.profiles[category].done()
        if self.print_progress:
            print("# %s done (%s)" % (category, self.profiles[category].runtime))


def sort_filter_mails(
    mails_to_show,
    do_find_ancestors_from_cache,
    mails_filter,
    list_decorator,
    show_thread_of,
    runtime_profile,
    runtime_profiles,
):
    if runtime_profiles is not None:
        runtime_profiles.start("threads_extract")

    timestamp = time.time()
    threads = threads_of(mails_to_show, do_find_ancestors_from_cache)
    sort_threads_by = list_decorator.sort_threads_by
    for sort_category in sort_threads_by:
        sort_threads(threads, sort_category)
    descend = not list_decorator.ascend
    if descend:
        threads.reverse()

    # sort patch series in patch order
    # should we have an option to skip this sort?  maybe, but the usage of such
    # option is unclear.
    for thread in threads:
        thread.replies.sort(key=lambda t: t.series[0] if t.series is not None else 0)

    runtime_profile.append(["threads_extract", time.time() - timestamp])
    if runtime_profiles is not None:
        runtime_profiles.end("threads_extract")
        runtime_profiles.start("set_index")

    by_pr_idx = []
    timestamp = time.time()
    mail_idx_key_map = {}
    for mail in threads:
        set_index(mail, by_pr_idx, 0, mail_idx_key_map)
    runtime_profile.append(["set_index", time.time() - timestamp])
    if runtime_profiles is not None:
        runtime_profiles.end("set_index")
        runtime_profiles.start("filtering")

    timestamp = time.time()
    # Show all by default
    if show_thread_of is None:
        start_idx = 0
        end_idx = list_decorator.max_len
        if end_idx is None:
            end_idx = len(mails_to_show)
    else:
        mail = by_pr_idx[show_thread_of]
        root = root_of_thread(mail)
        start_idx = root.pridx
        end_idx = root.pridx + nr_replies_of(root) + 1
    ls_range = range(start_idx, end_idx)

    filtered_mails = get_filtered_mails(by_pr_idx, ls_range, mails_filter)

    runtime_profile.append(["filtering", time.time() - timestamp])
    if runtime_profiles is not None:
        runtime_profiles.end("filtering")
    return filtered_mails, mail_idx_key_map


def child_of_collapsed(mail, mails_to_collapse):
    if mail.parent_mail is None:
        return False
    if mail.parent_mail.pridx in mails_to_collapse:
        return True
    return child_of_collapsed(mail.parent_mail, mails_to_collapse)


def fmt_mails_text(mails, list_decorator, mails_to_collapse):
    line_nr_to_mail_map = {}
    lines = []
    if len(mails) == 0:
        return lines, line_nr_to_mail_map
    collapse_threads = list_decorator.collapse
    show_url = list_decorator.show_url
    nr_cols = list_decorator.cols

    max_index = mails[-1].pridx
    if max_index == 0:
        max_index = 1
    max_digits_for_idx = math.ceil(math.log(max_index, 10))

    if mails_to_collapse:
        # set parent_mail
        # set do_find_ancestors_from_cache as False, since the caller should
        # already did that before.
        threads_of(mails, do_find_ancestors_from_cache=False)

    for mail in mails:
        show_nr_replies = False
        if collapse_threads == True:
            if mail.prdepth > 0:
                continue
            show_nr_replies = True
        if mail.pridx in mails_to_collapse:
            show_nr_replies = True
        if child_of_collapsed(mail, mails_to_collapse):
            continue
        mail_lines = format_entry(
            mail, max_digits_for_idx, show_nr_replies, show_url, nr_cols
        )
        for line_nr in range(len(lines), len(lines) + len(mail_lines)):
            line_nr_to_mail_map[line_nr] = mail
        lines += mail_lines
    return lines, line_nr_to_mail_map


def format_stat_lines(mails_to_show, filtered_mails, stat_authors):
    stat_lines = []
    total_stat_lines = format_stat(mails_to_show, stat_authors)
    filtered_stat_lines = format_stat(filtered_mails, stat_authors)
    if total_stat_lines == filtered_stat_lines:
        stat_lines += total_stat_lines
    else:
        stat_lines.append("# stat for total mails")
        stat_lines += total_stat_lines
        stat_lines.append("#")
        stat_lines.append("# stat for filtered mails")
        stat_lines += filtered_stat_lines
    return stat_lines


def format_runtime_profile_lines(
    runtime_profile, show_always, timestamp, runtime_profiles
):
    runtime_profile_lines = []
    total_profiled_time = sum([profile[1] for profile in runtime_profile])
    if not show_always and total_profiled_time < 3:
        return []
    runtime_profile.append(["etc", time.time() - timestamp])
    if runtime_profiles is not None:
        runtime_profiles.end("etc")
    runtime_profile_lines = ["# runtime profile"]
    for key, value in runtime_profile:
        runtime_profile_lines.append("# %s: %s" % (key, value))
    runtime_profile_lines.append("#")
    return runtime_profile_lines


class MailsListData:
    # formatted text of the list
    text = None
    # number of comment lines for stat and runtime profile
    len_comments = None
    comments_lines = None
    mail_lines = None
    # line number of mail of the line map
    # line number starts from non-comment
    line_nr_mail_map = None
    # mail print index to cached mail key map
    mail_idx_key_map = None

    def __init__(self, text, len_comments, line_nr_mail_map, mail_idx_key_map):
        self.text = text
        self.len_comments = len_comments
        self.line_nr_mail_map = line_nr_mail_map
        self.mail_idx_key_map = mail_idx_key_map
        if self.text is None:
            lines = []
        else:
            lines = text.split("\n")
        self.comments_lines = lines[:len_comments]
        self.mail_lines = lines[len_comments:]

    def append_comments(self, comments_lines):
        self.comments_lines += comments_lines
        self.len_comments += len(comments_lines)
        self.text = "\n".join(self.comments_lines + self.mail_lines)


def mails_to_list_data(
    mails_to_show,
    do_find_ancestors_from_cache,
    mails_filter,
    list_decorator,
    show_thread_of,
    runtime_profile,
    stat_only,
    stat_authors,
    print_progress=False,
    runtime_profiles=None,
):
    """Return MailsListData and an error"""
    if len(mails_to_show) == 0:
        return None, "no mail to list"

    filtered_mails, mail_idx_key_map = sort_filter_mails(
        mails_to_show,
        do_find_ancestors_from_cache,
        mails_filter,
        list_decorator,
        show_thread_of,
        runtime_profile,
        runtime_profiles,
    )

    timestamp = time.time()
    if runtime_profiles is not None:
        runtime_profiles.start("etc")

    lines, line_nr_to_mail_map = fmt_mails_text(
        filtered_mails, list_decorator, mails_to_collapse={}
    )

    stat_lines = []
    if not list_decorator.hide_stat:
        stat_lines = format_stat_lines(mails_to_show, filtered_mails, stat_authors)

    runtime_profile_lines = format_runtime_profile_lines(
        runtime_profile, list_decorator.runtime_profile, timestamp, runtime_profiles
    )

    if stat_only:
        text = "\n".join(stat_lines)
        len_comments = len(stat_lines)
    else:
        text = "\n".join(runtime_profile_lines + stat_lines + lines)
        len_comments = len(runtime_profile_lines) + len(stat_lines)
    return (
        MailsListData(text, len_comments, line_nr_to_mail_map, mail_idx_key_map),
        None,
    )


def git_log_output_line_to_mail(line, mdir):
    fields = line.split()
    if len(fields) < 3:
        return None
    subject_offset = len(fields[0]) + 1 + len(fields[1]) + 1
    subject = line[subject_offset:]
    return _hkml.Mail.from_gitlog(fields[0], mdir, fields[1], subject)


def warn_old_epochs(mails, since, oldest_epoch):
    if oldest_epoch == 0:
        return
    if since is None:
        return
    if len(mails) == 0 or mails[-1].date - since > datetime.timedelta(months=1):
        print("you might need to fetch old epochs")


def gitlog_date_misordered(mdir, oldest_commit):
    cmd = [
        "git",
        "--git-dir=%s" % mdir,
        "log",
        "--date=iso-strict",
        "--pretty=%H %ad %s",
        "%s^" % oldest_commit,
        "-2",
    ]
    two_more_logs = _hkml.cmd_lines_output(cmd)
    if len(two_more_logs) != 2:
        return False
    newer = datetime.datetime.fromisoformat(two_more_logs[0].split()[1]).astimezone()
    older = datetime.datetime.fromisoformat(two_more_logs[1].split()[1]).astimezone()
    return newer < older


def handle_gitlog_date_misorders(lines, mdir, since, commits_range, max_nr_mails):
    if since is None:
        return
    if commits_range is not None:
        return
    if max_nr_mails is not None and len(lines) == max_nr_mails:
        return
    if len(lines) == 0:
        return lines
    oldest_fields = lines[-1].split()
    oldest_commit = oldest_fields[0]
    if not gitlog_date_misordered(mdir, oldest_commit):
        return lines

    print("# date misorder found...")

    base_cmd = [
        "git",
        "--git-dir=%s" % mdir,
        "log",
        "--date=iso-strict",
        "--pretty=%H %ad %s",
    ]
    while True:
        more_logs = _hkml.cmd_lines_output(base_cmd + ["%s^" % oldest_commit, "-300"])
        if len(more_logs) == 0:
            break
        for line in more_logs:
            the_fields = line.split()
            the_date = datetime.datetime.fromisoformat(the_fields[1]).astimezone()
            if the_date > since:
                lines.append(line)
        more_oldest_fields = more_logs[-1].split()
        oldest_commit = more_oldest_fields[0]
        oldest_date = datetime.datetime.fromisoformat(
            more_oldest_fields[1]
        ).astimezone()
        if oldest_date < since and not gitlog_date_misordered(mdir, oldest_commit):
            break


def get_mails_gitlog_lines(
    mdir, since, until, min_nr_mails, max_nr_mails, commits_range
):
    lines = []
    if not os.path.isdir(mdir):
        return lines
    base_cmd = [
        "git",
        "--git-dir=%s" % mdir,
        "log",
        "--date=iso-strict",
        "--pretty=%H %ad %s",
    ]
    if commits_range is not None:
        base_cmd += [commits_range]

    cmd = base_cmd + []

    if since is not None:
        cmd += ["--since=%s" % since.strftime("%Y-%m-%d %H:%M:%S")]
    if until:
        cmd += ["--until=%s" % until.strftime("%Y-%m-%d %H:%M:%S")]
    if max_nr_mails is not None:
        cmd += ["-n", max_nr_mails]
    try:
        lines = _hkml.cmd_lines_output(cmd)
    except:
        # maybe commits_range is given, but the commit is not in this mdir
        pass

    if min_nr_mails is not None and len(lines) < min_nr_mails:
        cmd = base_cmd + ["-n", "%d" % min_nr_mails]
        if until:
            cmd += ["--until=%s" % until]
        try:
            lines = _hkml.cmd_lines_output(cmd)
        except:
            # maybe commits_range is given, but the commit is not in this
            # mdir
            pass

    handle_gitlog_date_misorders(lines, mdir, since, commits_range, max_nr_mails)
    return lines


def get_mails_from_git(
    mail_list, since, until, min_nr_mails, max_nr_mails, commits_range=None
):
    lines = []
    mdirs = _hkml.mail_list_data_paths(mail_list)
    if not mdirs:
        return None, "Mailing list '%s' in manifest not found." % mail_list

    mails = []
    for mdir in mdirs:
        lines = get_mails_gitlog_lines(
            mdir, since, until, min_nr_mails, max_nr_mails, commits_range
        )
        for line in lines:
            mail = git_log_output_line_to_mail(line, mdir)
            # mbox can be empty string if the commit is invalid one.
            if mail is None or mail.mbox == "":
                continue
            mails.append(mail)
    warn_old_epochs(mails, since, _hkml.get_epoch_from_git_path(mdirs[-1]))
    return mails, None


def infer_source_type(source, is_pisearch):
    """Return source type and error string"""
    candidates = []

    if source == "clipboard":
        candidates.append("clipboard")
    if os.path.isfile(source):
        candidates.append("mbox")
    if hkml_tag.tag_exists(source):
        candidates.append("tag")
    if _hkml.is_valid_mail_list(source):
        candidates.append("mailing_list")
    elif source == "all" and is_pisearch is True:
        candidates.append("mailing_list")
    if "@" in source:
        candidates.append("msgid")

    if len(candidates) == 0:
        return None, "no candidate"
    elif len(candidates) > 1:
        return None, "multiple candidates (%s)" % ", ".join(candidates)
    return candidates[0], None


def pisearch_tag(node):
    prefix = "{http://www.w3.org/2005/Atom}"
    if not node.tag.startswith(prefix):
        return ""
    return node.tag[len(prefix) :]


def get_mails_from_atom(atom_file, mailing_list):
    try:
        root = ET.parse(atom_file).getroot()
    except Exception as e:
        # no results found case atom cannot be parsed for some unknown reason.
        with open(atom_file, "r") as f:
            content = f.read()
        if content.find("[No results found]") != -1:
            return [], None
        return None, "parsing atom file at %s failed (%s)" % (atom_file, e)
    entries = [node for node in root if pisearch_tag(node) == "entry"]
    mails = []
    for entry in entries:
        mails.append(_hkml.Mail(atom_entry=entry, atom_ml=mailing_list))
    return mails, None


def get_mails_from_pisearch(mailing_list, query_str):
    """Get mails from public inbox search query"""
    pi_url = _hkml.get_manifest()["site"]
    query_str = query_str.replace(" ", "+")
    query_url = "%s/%s/?q=%s&x=A" % (pi_url, mailing_list, query_str)
    _, query_output = tempfile.mkstemp(prefix="hkml_pisearch_atom-")
    if not hkml_common.cmd_available("curl"):
        return None, '"which curl" fails'

    _hkml.delay_public_inbox_query()
    if (
        subprocess.call(
            ["curl", query_url, "-o", query_output], stderr=subprocess.DEVNULL
        )
        != 0
    ):
        return None, "fetching query result from %s failed" % query_url
    mails, err = get_mails_from_atom(query_output, mailing_list)
    if err is not None:
        return None, "parsing query (%s) output failed (%s)" % (query_url, err)
    os.remove(query_output)
    return mails, err


def manifest_might_be_outdated(mails, until):
    if len(mails) > 0 or not _hkml.is_for_lore_kernel_org():
        return False
    # hkml_monitor calls get_mails() with None until
    if until is None:
        return False
    return datetime.datetime.now() - until < datetime.timedelta(minutes=5)


def fetch_get_mails_from_git(
    fetch, source, since, until, min_nr_mails, max_nr_mails, commits_range
):
    if fetch:
        hkml_fetch.fetch_mail([source], True, 1)

    mails, err = get_mails_from_git(
        source, since, until, min_nr_mails, max_nr_mails, commits_range
    )
    if err is not None:
        return None, err

    if manifest_might_be_outdated(mails, until):
        print(
            " ".join(
                [
                    "No mail has fetched from '%s'." % source,
                    "You _might_ need to run 'hkml manifest fetch_lore'.",
                ]
            )
        )

    return mails, None


def get_thread_mails_from_web(msgid):
    if msgid.startswith("<") and msgid.endswith(">"):
        msgid = msgid[1:-1]
    # public inbox url could also be received.
    if msgid.startswith("http"):
        fields = msgid.split("/")
        for field in fields:
            if "@" in field:
                msgid = field
                break
    tmp_path = tempfile.mkdtemp(prefix="hkml_thread_")
    pi_url = _hkml.get_manifest()["site"]
    down_url = "%s/all/%s/t.mbox.gz" % (pi_url, msgid)
    _hkml.delay_public_inbox_query()
    if (
        subprocess.call(
            ["wget", down_url, "--directory-prefix=%s" % tmp_path],
            stderr=subprocess.DEVNULL,
        )
        != 0
    ):
        return None, "downloading mbox failed"
    if subprocess.call(["gunzip", os.path.join(tmp_path, "t.mbox.gz")]) != 0:
        return None, "extracting mbox failed"
    mails, err = get_mails(
        os.path.join(tmp_path, "t.mbox"), False, None, None, None, None
    )
    os.remove(os.path.join(tmp_path, "t.mbox"))
    os.rmdir(tmp_path)
    if err is not None:
        return None, "parsing mbox failed (%s)" % err

    deduped_mails = []
    msgids = {}
    for mail in mails:
        msgid = mail.get_field("message-id")
        if msgid in msgids:
            continue
        msgids[msgid] = True
        deduped_mails.append(mail)
    return deduped_mails, None


def get_mails(
    source,
    fetch,
    since,
    until,
    min_nr_mails,
    max_nr_mails,
    commits_range=None,
    source_type=None,
    pisearch=None,
):
    if source_type is None:
        source_type, err = infer_source_type(source, pisearch is not None)
        if err is not None:
            return None, "\n".join(
                [
                    "source type inference for %s failed: %s" % (source, err),
                    "you could use --source_type option to solve this",
                ]
            )

    if source_type == "clipboard":
        mails, err = _hkml.read_mails_from_clipboard()
        if err != None:
            return None, "reading mails from clipboard failed: %s" % err
        if max_nr_mails is not None:
            mails = mails[:max_nr_mails]
        mails.sort(key=lambda mail: mail.date)
        return mails, None

    if source_type == "mbox":
        mails = _hkml.read_mbox_file(source)
        if max_nr_mails is not None:
            mails = mails[:max_nr_mails]
        mails.sort(key=lambda mail: mail.date)
        return mails, None

    if source_type == "tag":
        return hkml_tag.mails_of_tag(source), None

    if pisearch:
        return get_mails_from_pisearch(source, pisearch)

    if source_type == "msgid":
        mails, err = get_thread_mails_from_web(source)
        if err is not None:
            return None, "failed: %s for %s" % (err, source)
        return mails, None

    mails, err = fetch_get_mails_from_git(
        fetch, source, since, until, min_nr_mails, max_nr_mails, commits_range
    )
    if err is not None:
        return None, "failed: %s for %s" % (err, source)

    mails.reverse()
    return mails, None


def get_mails_from_multiple_sources(
    sources,
    do_fetch,
    since,
    until,
    min_nr_mails,
    max_nr_mails,
    source_types,
    do_pisearch,
):
    mails = []
    msgids = {}
    for idx, source in enumerate(sources):
        total_mails, err = get_mails(
            source,
            do_fetch,
            since,
            until,
            min_nr_mails,
            max_nr_mails,
            None,
            source_types[idx],
            do_pisearch,
        )
        if err is not None:
            return None, err
        for mail in total_mails:
            msgid = mail.get_field("message-id")
            if not msgid in msgids:
                mails.append(mail)
            msgids[msgid] = True

    if max_nr_mails is not None:
        mails = mails[:max_nr_mails]

    return mails, None


def show_list(text, to_stdout, to_less, mail_idx_key_map):
    if to_stdout:
        print(text)
        return
    hkml_open.pr_with_pager_if_needed(text)


def validate_set_source_type(args):
    if args.source_type is not None:
        if len(args.source_type) == 1:
            args.source_type = args.source_type * len(args.sources)
        else:
            return "numbers of --source_type and --sources mismatch"
    else:
        args.source_type = []
        for source in args.sources:
            source_type, err = infer_source_type(source, args.pisearch is not None)
            if err is not None:
                return "\n".join(
                    [
                        "source type inference for %s failed: %s" % (source, err),
                        "you could use --source_type option to solve this",
                    ]
                )
            args.source_type.append(source_type)
    return None


def disable_ancestor_finding_for_tags(args):
    """For tag-based listing, do_find_ancestors_from_cache can add unexpected
    mails of different tags.  Prevent it."""
    if args.do_find_ancestors_from_cache is False:
        return
    if len(args.source_type) == 0:
        return
    for source_type in args.source_type:
        if source_type != "tag":
            return
    args.do_find_ancestors_from_cache = False


def args_to_mails_list_data(args):
    # return MailsListData and error
    # if cached output is used, line_nr_to_mail_map and len_comments of the
    # list data becomes None.  Caller should make it when those on demand.
    err = validate_set_source_type(args)
    if err is not None:
        return None, err
    disable_ancestor_finding_for_tags(args)

    lists_cache_key = args_to_lists_cache_key(args)
    use_cached_output = True
    for source_type in args.source_type:
        if source_type != "mailing_list":
            use_cached_output = False
            break
    if args.ignore_cache is True:
        use_cached_output = False
    if use_cached_output and (args.fetch == False or args.sources == []):
        if args.sources == []:
            to_show, mail_idx_key_map = _hkml_list_cache.get_last_list()
            if to_show is None:
                return None, "no valid last list output exists"
        else:
            to_show, mail_idx_key_map = _hkml_list_cache.get_list_for(lists_cache_key)
        if to_show is not None:
            _hkml_list_cache.writeback_list_output()
            return MailsListData(to_show, None, None, mail_idx_key_map), None
    else:
        for source in args.sources:
            _hkml_list_cache.invalidate_cached_outputs(source)

    if args.since is None:
        since = datetime.datetime.now() - datetime.timedelta(days=3)
    else:
        since, err = hkml_common.parse_date_arg(args.since)
        if err is not None:
            return None, "parsing --since fail (%s)" % err
    if args.until is None:
        until = datetime.datetime.now() + datetime.timedelta(days=1)
    else:
        until, err = hkml_common.parse_date_arg(args.until)
        if err is not None:
            return None, "parsing --until fail (%s)" % err

    if args.nr_mails is not None:
        since = (until - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        args.min_nr_mails = args.nr_mails
        args.max_nr_mails = args.nr_mails

    if args.cols is None:
        try:
            args.cols = int(os.get_terminal_size().columns * 9 / 10)
        except OSError as e:
            pass

    runtime_profiles = RuntimeProfiles(using_hkml_view(args))
    runtime_profiles.start("get_mails")

    timestamp = time.time()
    runtime_profile = []
    mails_to_show, err = get_mails_from_multiple_sources(
        args.sources,
        args.fetch,
        since,
        until,
        args.min_nr_mails,
        args.max_nr_mails,
        args.source_type,
        args.pisearch,
    )
    if err is not None:
        return None, "getting mails failed (%s)" % err
    runtime_profile = [["get_mails", time.time() - timestamp]]
    runtime_profiles.end("get_mails")

    list_data, err = mails_to_list_data(
        mails_to_show,
        args.do_find_ancestors_from_cache,
        MailListFilter(args),
        MailListDecorator(args),
        None,
        runtime_profile,
        args.stat_only,
        args.stat_authors,
        using_hkml_view(args),
        runtime_profiles,
    )
    if err is not None:
        return None, err
    if args.source_type == ["msgid"]:
        for line_nr, mail in list_data.line_nr_mail_map.items():
            # drop enclosing <>
            mail_msgid = mail.get_field("message-id")[1:-1]
            if mail_msgid in args.sources[0]:
                lines = list_data.text.split("\n")
                comment = "# mail of the msgid is at row %d (%s ...)" % (
                    line_nr + list_data.len_comments + 1,
                    lines[line_nr + list_data.len_comments][:45],
                )
                list_data.append_comments([comment])
                break

    hkml_cache.writeback_mails()
    _hkml_list_cache.set_item(lists_cache_key, list_data)

    return list_data, None


def print_options_for(category):
    parser = argparse.ArgumentParser(add_help=False)
    if category == "filtering":
        add_mails_filter_arguments(parser)
    elif category == "decoration":
        add_decoration_arguments(parser, show_help=True)
    elif category == "advanced":
        add_advanced_arguments(parser, show_help=True)
    help_msg = parser.format_help()
    usage_msg, options_msg = help_msg.split("\n\n")
    print("\n".join(options_msg.split("\n")[1:]))


def using_hkml_view(args):
    return not args.stdout and not args.use_less


def main(args):
    if args.options_for is not None:
        print_options_for(args.options_for)
        return
    if args.read_dates:
        err = validate_set_source_type(args)
        if err is not None:
            print(err)
            exit(1)
        lists_cache_key = args_to_lists_cache_key(args)
        last_dates = _hkml_list_cache.get_cache_creation_dates(lists_cache_key)
        for idx, last_date in enumerate(last_dates):
            print(
                " %2d. %s (%s before)"
                % (idx, last_date, datetime.datetime.now() - last_date)
            )
        return 0

    if using_hkml_view(args):
        return hkml_view.gen_view_mails_list(args)
    list_data, err = args_to_mails_list_data(args)
    if err is not None:
        print(err)
        exit(1)
    show_list(list_data.text, args.stdout, args.use_less, list_data.mail_idx_key_map)


def add_mails_filter_arguments(parser):
    parser.add_argument(
        "--keywords",
        metavar="<word>",
        nargs="+",
        action="append",
        help=" ".join(
            [
                "Keywords to filter-in mails for.",
                'Format is: "<field> <keyword>...".',
                '<field> can be "from", "from_to", "from_to_cc", "subject",',
                'or "body".',
            ]
        ),
    )
    parser.add_argument(
        "--from_keywords",
        "--from",
        metavar="<keyword>",
        nargs="+",
        action="append",
        help=argparse.SUPPRESS,
    )
    # show mails having the keywords in from: field
    parser.add_argument(
        "--from_to_keywords",
        "--from_to",
        metavar="<keyword>",
        nargs="+",
        action="append",
        help=argparse.SUPPRESS,
    )
    # same to --from except chekcing to: fields together
    parser.add_argument(
        "--from_to_cc_keywords",
        "--from_to_cc",
        metavar="<keyword>",
        nargs="+",
        action="append",
        help=argparse.SUPPRESS,
    )
    # same to --from except chekcing to: and cc: fields together
    parser.add_argument(
        "--subject_keywords",
        "--subject",
        metavar="<words>",
        type=str,
        nargs="+",
        action="append",
        help=argparse.SUPPRESS,
    )
    # list mails containing the keyword in their subject
    parser.add_argument(
        "--body_keywords",
        "--body",
        metavar="<keyword>",
        type=str,
        nargs="+",
        action="append",
        help=argparse.SUPPRESS,
    )
    # list mails containing the keyword in their body
    parser.add_argument(
        "--new", "-n", action="store_true", help="list new threads only"
    )
    parser.add_argument(
        "--keywords_for",
        choices=["each", "root", "thread"],
        default="each",
        help="keywords applying target mails",
    )
    parser.add_argument(
        "--patches_for",
        metavar="<word>",
        nargs="+",
        help=" ".join(
            [
                "Filter for patches.",
                '"review" for patches not yet having Reviewed-by.',
                '"pick" for patches having Reviewed-by.',
                '"reviewer <reviewer>" for patches for specific reviewer.',
            ]
        ),
    )


def add_decoration_arguments(parser, show_help):
    parser.add_argument(
        "--collapse",
        "-c",
        action="store_true",
        help="collapse threads" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--sort_threads_by",
        nargs="+",
        default=["last_date"],
        choices=["first_date", "last_date", "nr_replies", "nr_comments"],
        help="threads sort keys" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--ascend",
        action="store_true",
        help="sort threads in ascending order" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--hot",
        action="store_true",
        help=(
            "show threads having more comments and later updated first."
            if show_help
            else argparse.SUPPRESS
        ),
    )
    parser.add_argument(
        "--cols",
        metavar="<int>",
        type=int,
        help="number of columns for each line" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--url",
        action="store_true",
        help="print URLs of the mails" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--hide_stat",
        action="store_true",
        help="hide stat of the mails" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--runtime_profile",
        action="store_true",
        help="print runtime profiling result" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--max_len_list",
        metavar="<int>",
        type=int,
        help="max length of the list" if show_help else argparse.SUPPRESS,
    )


def add_advanced_arguments(parser, show_help):
    parser.add_argument(
        "--nr_mails",
        type=int,
        metavar="<int>",
        help="number of mails to list" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--min_nr_mails",
        metavar="<int>",
        type=int,
        default=50,
        help="minimum number of mails to list" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--max_nr_mails",
        metavar="<int>",
        type=int,
        help="maximum number of mails to list" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--dont_find_ancestors_from_cache",
        action="store_false",
        dest="do_find_ancestors_from_cache",
        help=(
            "find missing thread ancestors from cache"
            if show_help
            else argparse.SUPPRESS
        ),
    )
    parser.add_argument(
        "--pisearch",
        metavar="<query>",
        help=(
            "get mails via given public inbox search query"
            if show_help
            else argparse.SUPPRESS
        ),
    )
    parser.add_argument(
        "--stat_only",
        action="store_true",
        help="print statistics only" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--stat_authors",
        action="store_true",
        help="print mail authors statistics" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--ignore_cache",
        action="store_true",
        help="ignore cached previous list output" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help=(
            "print to stdout instead of using the pager"
            if show_help
            else argparse.SUPPRESS
        ),
    )
    parser.add_argument(
        "--use_less",
        action="store_true",
        help="use 'less' for output paging" if show_help else argparse.SUPPRESS,
    )
    parser.add_argument(
        "--read_dates",
        action="store_true",
        help="print last dates that read the list" if show_help else argparse.SUPPRESS,
    )
    _hkml.set_manifest_option(parser)


def set_argparser(parser=None):
    parser.description = "list mails"
    # What mails to show
    parser.add_argument(
        "sources",
        metavar="<source of mails>",
        nargs="*",
        help="  ".join(
            [
                "Source of mails to list.  Could be one of following types.",
                "1) Name of a mailing list in the manifest file.",
                "2) Message-Id of a mail in the thread to list.",
                "3) Path to mbox file in the local filesyste.",
                "4) Special keyword, 'clipboard'.",
                "'clipboard' means mbox string in the clipboard.",
                "5) 'hkml tag'-added tag.",
                "6) If nothing is given, show last list output.",
            ]
        ),
    )
    parser.add_argument(
        "--source_type",
        nargs="+",
        choices=["mailing_list", "msgid", "mbox", "clipboard", "tag"],
        help="type of sources",
    )
    parser.add_argument(
        "--fetch", action="store_true", help="fetch mails before listing"
    )
    hkml_common.add_date_arg(parser, "--since", "show mails sent after this.")
    hkml_common.add_date_arg(parser, "--until", "show mails sent before this.")

    add_mails_filter_arguments(parser)
    add_decoration_arguments(parser, show_help=False)

    # this option is handled by hkml_view_mails
    hkml_common.add_date_arg(parser, "--dim_old", "dim mails older than this.")

    add_advanced_arguments(parser, show_help=False)

    parser.add_argument(
        "--options_for",
        choices=["filtering", "decoration", "advanced"],
        help="show help messages of options for given purpose",
    )

    parser.epilog += " ".join(
        ["\nThere are advanced hidden options.", "Use --options_for to show them."]
    )
