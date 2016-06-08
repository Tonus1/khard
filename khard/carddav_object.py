# -*- coding: utf-8 -*-

# contact object class
# vcard: https://tools.ietf.org/html/rfc6350

import os
import sys
import datetime
import re
import vobject
import yaml
from atomicwrites import atomic_write
from . import helpers
from .object_type import ObjectType

class CarddavObject:
    def __init__(self, address_book, filename = None):
        self.vcard = None
        self.address_book = address_book
        self.filename = filename

        # vcard supports the following type values
        self.supported_phone_types = ["bbs", "car", "cell", "fax", "home", "isdn",
                "msg", "modem", "pager", "pcs", "pref", "video", "voice", "work"]
        self.supported_email_types = ["home", "internet", "pref", "uri", "work", "x400"]
        self.supported_address_types = ["home", "pref", "work"]

        # load vcard
        if self.filename is None:
            # create new vcard object
            self.vcard = vobject.vCard()
            # uid
            uid_obj = self.vcard.add('uid')
            uid_obj.value = helpers.get_random_uid()
            # use uid for vcard filename
            self.filename = os.path.join(address_book.get_path(),
                    self.vcard.uid.value + ".vcf")

        else:
            # create vcard from .vcf file
            try:
                file = open(self.filename, "r")
                contents = file.read()
                file.close()
            except IOError as e:
                raise
            # create vcard object
            try:
                self.vcard = vobject.readOne(contents)
            except vobject.base.ParseError as e:
                # if creation fails, try to repair vcard contents
                try:
                    self.vcard = vobject.readOne(
                            self.filter_invalid_tags(contents))
                    self.write_to_file(overwrite=True)
                except vobject.base.ParseError as e:
                    raise


    #######################################
    # factory methods to create new contact
    #######################################

    @classmethod
    def new_contact(cls, address_book):
        """ use this to create a new and empty contact """
        return cls(address_book)

    @classmethod
    def from_file(cls, address_book, filename):
        """ Use this if you want to create a new contact from an existing .vcf file """
        return cls(address_book, filename)

    @classmethod
    def from_user_input(cls, address_book, user_input):
        """ Use this if you want to create a new contact from user input """
        contact = cls(address_book)
        contact.process_user_input(user_input)
        return contact

    @classmethod
    def from_existing_contact_with_new_user_input(cls, contact, user_input):
        """ use this if you want to clone an existing contact and  replace its data with new user input in one step """
        contact = cls(contact.get_address_book(), contact.get_filename())
        contact.process_user_input(user_input)
        return contact


    ######################################
    # overwrite some default class methods
    ######################################

    def __str__(self):
        return self.get_full_name()

    def __eq__(self, other):
        return isinstance(other, CarddavObject) \
                and self.print_vcard(show_address_book=False, show_uid=False) == other.print_vcard(show_address_book=False, show_uid=False)

    def __ne__(self, other):
        return not self == other


    #####################
    # getters and setters
    #####################

    def get_filename(self):
        return self.filename

    def set_filename(self, filename):
        self.filename = filename

    def get_address_book(self):
        return self.address_book

    def get_rev(self):
        """
        :rtype: str
        """
        try:
            return self.vcard.rev.value
        except AttributeError as e:
            return ""

    def add_rev(self, dt):
        rev_obj = self.vcard.add('rev')
        rev_obj.value = "%.4d%.2d%.2dT%.2d%.2d%.2dZ" \
                % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)

    def get_uid(self):
        """
        :rtype: str
        """
        try:
            return self.vcard.uid.value
        except AttributeError as e:
            return ""

    def add_uid(self, uid):
        uid_obj = self.vcard.add('uid')
        uid_obj.value = helpers.convert_to_vcard(
                "uid", uid, ObjectType.string)

    def get_name_prefixes(self):
        """
        :rtype: list(str)
        """
        try:
            prefix_list = self.vcard.n.value.prefix
        except AttributeError as e:
            prefix_list = []
        else:
            # check if list only contains an empty string ([""])
            if not ''.join(prefix_list):
                prefix_list = []
        return prefix_list if isinstance(prefix_list, list) else [prefix_list]

    def get_first_names(self):
        """
        :rtype: list(str)
        """
        try:
            first_name_list = self.vcard.n.value.given
        except AttributeError as e:
            first_name_list = []
        else:
            # check if list only contains an empty string ([""])
            if not ''.join(first_name_list):
                first_name_list = []
        return first_name_list if isinstance(first_name_list, list) \
                else [first_name_list]

    def get_additional_names(self):
        """
        :rtype: list(str)
        """
        try:
            additional_name_list = self.vcard.n.value.additional
        except AttributeError as e:
            additional_name_list = []
        else:
            # check if list only contains an empty string ([""])
            if not ''.join(additional_name_list):
                additional_name_list = []
        return additional_name_list if isinstance(additional_name_list, list) \
                else [additional_name_list]

    def get_last_names(self):
        """
        :rtype: list(str)
        """
        try:
            last_name_list = self.vcard.n.value.family
        except AttributeError as e:
            last_name_list = []
        else:
            # check if list only contains an empty string ([""])
            if not ''.join(last_name_list):
                last_name_list = []
        return last_name_list if isinstance(last_name_list, list) \
                else [last_name_list]

    def get_name_suffixes(self):
        """
        :rtype: list(str)
        """
        try:
            suffix_list = self.vcard.n.value.suffix
        except AttributeError as e:
            suffix_list = []
        else:
            # check if list only contains an empty string ([""])
            if not ''.join(suffix_list):
                suffix_list = []
        return suffix_list if isinstance(suffix_list, list) else [suffix_list]

    def get_full_name(self):
        """
        :rtype: str
        """
        try:
            return self.vcard.fn.value
        except AttributeError as e:
            return ""

    def get_first_name_last_name(self):
        """
        :rtype: str
        """
        if self.get_first_names() and self.get_last_names():
            return "%s %s" \
                    % (helpers.list_to_string(self.get_first_names(), " "),
                            helpers.list_to_string(self.get_last_names(), " "))
        elif self.get_first_names():
            return helpers.list_to_string(self.get_first_names(), " ")
        elif self.get_last_names():
            return helpers.list_to_string(self.get_last_names(), " ")
        else:
            return self.get_full_name()

    def get_last_name_first_name(self):
        """
        :rtype: str
        """
        if self.get_first_names() and self.get_last_names():
            return "%s %s" \
                    % (helpers.list_to_string(self.get_last_names(), " "),
                            helpers.list_to_string(self.get_first_names(), " "))
        elif self.get_first_names():
            return helpers.list_to_string(self.get_first_names(), " ")
        elif self.get_last_names():
            return helpers.list_to_string(self.get_last_names(), " ")
        else:
            return self.get_full_name()

    def add_name(self, prefix, first_name, additional_name, last_name, suffix):
        # n
        name_obj = self.vcard.add('n')
        name_obj.value = vobject.vcard.Name(
                prefix = helpers.convert_to_vcard(
                    "name prefix", prefix,
                    ObjectType.string_or_list_with_strings),
                given = helpers.convert_to_vcard(
                    "first name", first_name,
                    ObjectType.string_or_list_with_strings),
                additional = helpers.convert_to_vcard(
                    "additional name", additional_name,
                    ObjectType.string_or_list_with_strings),
                family = helpers.convert_to_vcard(
                    "last name", last_name,
                    ObjectType.string_or_list_with_strings),
                suffix = helpers.convert_to_vcard(
                    "name suffix", suffix,
                    ObjectType.string_or_list_with_strings))
        # fn
        if not self.vcard.getChildValue("fn") \
                and (self.get_first_names() or self.get_last_names()):
            names = []
            if self.get_name_prefixes():
                names += self.get_name_prefixes()
            if self.get_first_names():
                names += self.get_first_names()
            if self.get_last_names():
                names += self.get_last_names()
            if self.get_name_suffixes():
                names += self.get_name_suffixes()
            name_obj = self.vcard.add('fn')
            name_obj.value = helpers.list_to_string(names, " ")

    def get_organisations(self):
        """
        :returns: list of organisations, sorted alphabetically
        :rtype: list(list(str))
        """
        organisations = []
        for child in self.vcard.getChildren():
            if child.name == "ORG":
                if not isinstance(child.value, list):
                    # some newer versions of vobject module don't split the
                    # organisation attribute properly at the "," character
                    # so fix that by splitting at ?; manually and return a list
                    # whereas ? could be any char except the \ (backslash)
                    org_list = []
                    start_index = 0
                    for match in re.finditer("[^\\\\];", child.value):
                        org_list.append(
                                child.value[start_index:match.start()+1])
                        start_index = match.start()+2
                    child.value = org_list + [child.value[start_index:]]
                organisations.append(
                        [ x.replace("\\", "") for x in child.value ])
        return sorted(organisations)

    def add_organisation(self, organisation):
        org_obj = self.vcard.add('org')
        org_obj.value = helpers.convert_to_vcard(
                "organisation", organisation, ObjectType.list_with_strings)
        # check if fn attribute is already present
        if not self.vcard.getChildValue("fn") \
                and self.get_organisations():
            # if not, set fn to organisation name
            name_obj = self.vcard.add('fn')
            name_obj.value = helpers.list_to_string(
                    self.get_organisations()[0], ", ")
            showas_obj = self.vcard.add('x-abshowas')
            showas_obj.value = "COMPANY"

    def get_titles(self):
        """
        :rtype: list(list(str))
        """
        titles = []
        for child in self.vcard.getChildren():
            if child.name == "TITLE":
                titles.append(child.value)
        return sorted(titles)

    def add_title(self, title):
        title_obj = self.vcard.add('title')
        title_obj.value = helpers.convert_to_vcard(
                "title", title, ObjectType.string)

    def get_roles(self):
        """
        :rtype: list(list(str))
        """
        roles = []
        for child in self.vcard.getChildren():
            if child.name == "ROLE":
                roles.append(child.value)
        return sorted(roles)

    def add_role(self, role):
        role_obj = self.vcard.add('role')
        role_obj.value = helpers.convert_to_vcard(
                "role", role, ObjectType.string)

    def get_phone_numbers(self):
        """
        : returns: dict of type and phone number list
        :rtype: dict(str, list(str))
        """
        phone_dict = {}
        for child in self.vcard.getChildren():
            if child.name == "TEL":
                type = helpers.list_to_string(
                        self.get_types_for_vcard_object(child, "voice"), ", ")
                if phone_dict.get(type) is None:
                    phone_dict[type] = []
                phone_dict[type].append(child.value)
        # sort phone number lists
        for number_list in phone_dict.values():
            number_list.sort()
        return phone_dict

    def add_phone_number(self, type, number):
        phone_obj = self.vcard.add('tel')
        phone_obj.value = helpers.convert_to_vcard(
                "phone number", number, ObjectType.string)
        standard_types, custom_types = self.parse_type_value(
                helpers.string_to_list(type, ","),
                number, self.supported_phone_types)
        if len(standard_types) == 0 and len(custom_types) == 0:
            raise ValueError("Error: "
                    "label for phone number " + number + " is missing.")
        elif len(custom_types) > 1:
            raise ValueError("Error: "
                    "phone number " + number + " got more than one custom "
                    "label: " + helpers.list_to_string(custom_types, ", "))
        else:
            if standard_types:
                phone_obj.type_param = standard_types
            if custom_types:
                number_of_custom_phone_number_labels = 0
                for label in self.vcard.getChildren():
                    if label.name == "X-ABLABEL" \
                            and label.group.startswith("itemtel"):
                        number_of_custom_phone_number_labels += 1
                group_name = "itemtel%d" \
                        % (number_of_custom_phone_number_labels+1)
                phone_obj.group = group_name
                label_obj = self.vcard.add('x-ablabel')
                label_obj.group = group_name
                label_obj.value = custom_types[0]

    def get_email_addresses(self):
        """
        : returns: dict of type and email address list
        :rtype: dict(str, list(str))
        """
        email_dict = {}
        for child in self.vcard.getChildren():
            if child.name == "EMAIL":
                type = helpers.list_to_string(
                        self.get_types_for_vcard_object(child, "internet"), ", ")
                if email_dict.get(type) is None:
                    email_dict[type] = []
                email_dict[type].append(child.value)
        # sort email address lists
        for email_list in email_dict.values():
            email_list.sort()
        return email_dict

    def add_email_address(self, type, address):
        email_obj = self.vcard.add('email')
        email_obj.value = helpers.convert_to_vcard(
                "email address", address, ObjectType.string)
        standard_types, custom_types = self.parse_type_value(
                helpers.string_to_list(type, ","),
                address, self.supported_email_types)
        if len(standard_types) == 0 and len(custom_types) == 0:
            raise ValueError("Error: "
                    "label for email address " + address + " is missing.")
        elif len(custom_types) > 1:
            raise ValueError("Error: "
                    "email address " + address + " got more than one custom "
                    "label: " + helpers.list_to_string(custom_types, ", "))
        else:
            if standard_types:
                email_obj.type_param = standard_types
            if custom_types:
                number_of_custom_email_labels = 0
                for label in self.vcard.getChildren():
                    if label.name == "X-ABLABEL" \
                            and label.group.startswith("itememail"):
                        number_of_custom_email_labels += 1
                group_name = "itememail%d" % (number_of_custom_email_labels+1)
                email_obj.group = group_name
                label_obj = self.vcard.add('x-ablabel')
                label_obj.group = group_name
                label_obj.value = custom_types[0]

    def get_post_addresses(self):
        """
        : returns: dict of type and post address list
        :rtype: dict(str, list(dict(str,list|str)))
        """
        post_adr_dict = {}
        for child in self.vcard.getChildren():
            if child.name == "ADR":
                type = helpers.list_to_string(
                        self.get_types_for_vcard_object(child, "home"), ", ")
                if post_adr_dict.get(type) is None:
                    post_adr_dict[type] = []
                post_adr_dict[type].append(
                        {
                            "box" : child.value.box,
                            "extended" : child.value.extended,
                            "street" : child.value.street,
                            "code" : child.value.code,
                            "city" : child.value.city,
                            "region" : child.value.region,
                            "country" : child.value.country
                        })
        # sort post address lists
        for post_adr_list in post_adr_dict.values():
            post_adr_list.sort(
                    key=lambda x: (
                        helpers.list_to_string(x['city'], " ").lower(),
                        helpers.list_to_string(x['street'], " ").lower()))
        return post_adr_dict

    def get_formatted_post_addresses(self):
        formatted_post_adr_dict = {}
        for type, post_adr_list in self.get_post_addresses().items():
            formatted_post_adr_dict[type] = []
            for post_adr in post_adr_list:
                strings = []
                if post_adr.get("street"):
                    strings.append(
                            helpers.list_to_string(post_adr.get("street"), "\n"))
                if post_adr.get("box") and post_adr.get("extended"):
                    strings.append("%s %s" % (
                            helpers.list_to_string(post_adr.get("box"), " "),
                            helpers.list_to_string(post_adr.get("extended"), " ")))
                elif post_adr.get("box"):
                    strings.append(
                            helpers.list_to_string(post_adr.get("box"), " "))
                elif post_adr.get("extended"):
                    strings.append(
                            helpers.list_to_string(post_adr.get("extended"), " "))
                if post_adr.get("code") and post_adr.get("city"):
                    strings.append("%s %s" % (
                            helpers.list_to_string(post_adr.get("code"), " "),
                            helpers.list_to_string(post_adr.get("city"), " ")))
                elif post_adr.get("code"):
                    strings.append(
                            helpers.list_to_string(post_adr.get("code"), " "))
                elif post_adr.get("city"):
                    strings.append(
                            helpers.list_to_string(post_adr.get("city"), " "))
                if post_adr.get("region") and post_adr.get("country"):
                    strings.append("%s, %s" % (
                            helpers.list_to_string(post_adr.get("region"), " "),
                            helpers.list_to_string(post_adr.get("country"), " ")))
                elif post_adr.get("region"):
                    strings.append(
                            helpers.list_to_string(post_adr.get("region"), " "))
                elif post_adr.get("country"):
                    strings.append(
                            helpers.list_to_string(post_adr.get("country"), " "))
                formatted_post_adr_dict[type].append('\n'.join(strings))
        return formatted_post_adr_dict

    def add_post_address(
            self, type, box, extended, street, code, city, region, country):
        adr_obj = self.vcard.add('adr')
        adr_obj.value = vobject.vcard.Address(
                box = helpers.convert_to_vcard(
                    "box address field", box,
                    ObjectType.string_or_list_with_strings),
                extended = helpers.convert_to_vcard(
                    "extended address field", extended,
                        ObjectType.string_or_list_with_strings),
                street = helpers.convert_to_vcard(
                    "street", street, ObjectType.string_or_list_with_strings),
                code = helpers.convert_to_vcard(
                    "post code", code, ObjectType.string_or_list_with_strings),
                city = helpers.convert_to_vcard(
                    "city", city, ObjectType.string_or_list_with_strings),
                region = helpers.convert_to_vcard(
                    "region", region, ObjectType.string_or_list_with_strings),
                country = helpers.convert_to_vcard(
                    "country", country, ObjectType.string_or_list_with_strings))
        standard_types, custom_types = self.parse_type_value(
                helpers.string_to_list(type, ","),
                "%s, %s" % (street, city), self.supported_address_types)
        if len(standard_types) == 0 and len(custom_types) == 0:
            raise ValueError("Error: "
                    "label for post address " + street + " is missing.")
        elif len(custom_types) > 1:
            raise ValueError("Error: "
                    "post address " + street + " got more than one custom "
                    "label: " + helpers.list_to_string(custom_types, ", "))
        else:
            if standard_types:
                adr_obj.type_param = standard_types
            if custom_types:
                number_of_custom_post_address_labels = 0
                for label in self.vcard.getChildren():
                    if label.name == "X-ABLABEL" \
                            and label.group.startswith("itemadr"):
                        number_of_custom_post_address_labels += 1
                group_name = "itemadr%d" \
                        % (number_of_custom_post_address_labels+1)
                adr_obj.group = group_name
                label_obj = self.vcard.add('x-ablabel')
                label_obj.group = group_name
                label_obj.value = custom_types[0]

    def get_categories(self):
        """
        :rtype: list(str) or list(list(str))
        """
        category_list = []
        for child in self.vcard.getChildren():
            if child.name == "CATEGORIES":
                value = child.value
                category_list.append(
                        value if isinstance(value, list) else [value])
        if len(category_list) == 1:
            return category_list[0]
        return sorted(category_list)

    def add_category(self, categories):
        """ categories variable must be a list """
        categories_obj = self.vcard.add('categories')
        categories_obj.value = helpers.convert_to_vcard(
                "category", categories, ObjectType.list_with_strings)

    def get_nicknames(self):
        """
        :rtype: list(list(str))
        """
        nicknames = []
        for child in self.vcard.getChildren():
            if child.name == "NICKNAME":
                nicknames.append(child.value)
        return sorted(nicknames)

    def add_nickname(self, nickname):
        nickname_obj = self.vcard.add('nickname')
        nickname_obj.value = helpers.convert_to_vcard(
                "nickname", nickname, ObjectType.string)

    def get_notes(self):
        """
        :rtype: list(list(str))
        """
        notes = []
        for child in self.vcard.getChildren():
            if child.name == "NOTE":
                notes.append(child.value)
        return sorted(notes)

    def add_note(self, note):
        note_obj = self.vcard.add('note')
        note_obj.value = helpers.convert_to_vcard(
                "note", note, ObjectType.string)

    def get_jabber_ids(self):
        """
        :rtype: list(list(str))
        """
        jabber_ids = []
        for child in self.vcard.getChildren():
            if child.name == "X-JABBER":
                jabber_ids.append(child.value)
        return sorted(jabber_ids)

    def add_jabber_id(self, jabber_id):
        jabber_obj = self.vcard.add('x-jabber')
        jabber_obj.value = helpers.convert_to_vcard(
                "jabber id", jabber_id, ObjectType.string)

    def get_skype_ids(self):
        """
        :rtype: list(list(str))
        """
        skype_ids = []
        for child in self.vcard.getChildren():
            if child.name == "X-SKYPE":
                skype_ids.append(child.value)
        return sorted(skype_ids)

    def add_skype_id(self, skype_id):
        skype_obj = self.vcard.add('x-skype')
        skype_obj.value = helpers.convert_to_vcard(
                "skype id", skype_id, ObjectType.string)

    def get_twitter_ids(self):
        """
        :rtype: list(list(str))
        """
        twitter_ids = []
        for child in self.vcard.getChildren():
            if child.name == "X-TWITTER":
                twitter_ids.append(child.value)
        return sorted(twitter_ids)

    def add_twitter_id(self, twitter_id):
        twitter_obj = self.vcard.add('x-twitter')
        twitter_obj.value = helpers.convert_to_vcard(
                "twitter id", twitter_id, ObjectType.string)

    def get_webpages(self):
        """
        :rtype: list(list(str))
        """
        urls = []
        for child in self.vcard.getChildren():
            if child.name == "URL":
                urls.append(child.value)
        return sorted(urls)

    def add_webpage(self, webpage):
        webpage_obj = self.vcard.add('url')
        webpage_obj.value = helpers.convert_to_vcard(
                "webpage", webpage, ObjectType.string)

    def get_birthday(self):
        """:returns: contacts birthday or None if not available
            :rtype: datetime.datetime
        """
        try:
            return datetime.datetime.strptime(
                    self.vcard.bday.value.replace('-', ''), "%Y%m%d")
        except AttributeError as e:
            return None
        except ValueError as e:
            return None

    def add_birthday(self, date):
        bday_obj = self.vcard.add('bday')
        bday_obj.value = "%.4d%.2d%.2d" % (date.year, date.month, date.day)


    #######################
    # object helper methods
    #######################

    def filter_invalid_tags(self, contents):
        contents = re.sub('(?i)' + re.escape('X-messaging/aim-All'), 'X-AIM', contents)
        contents = re.sub('(?i)' + re.escape('X-messaging/gadu-All'), 'X-GADUGADU', contents)
        contents = re.sub('(?i)' + re.escape('X-messaging/groupwise-All'), 'X-GROUPWISE', contents)
        contents = re.sub('(?i)' + re.escape('X-messaging/icq-All'), 'X-ICQ', contents)
        contents = re.sub('(?i)' + re.escape('X-messaging/xmpp-All'), 'X-JABBER', contents)
        contents = re.sub('(?i)' + re.escape('X-messaging/msn-All'), 'X-MSN', contents)
        contents = re.sub('(?i)' + re.escape('X-messaging/yahoo-All'), 'X-YAHOO', contents)
        contents = re.sub('(?i)' + re.escape('X-messaging/skype-All'), 'X-SKYPE', contents)
        contents = re.sub('(?i)' + re.escape('X-messaging/irc-All'), 'X-IRC', contents)
        contents = re.sub('(?i)' + re.escape('X-messaging/sip-All'), 'X-SIP', contents)
        return contents

    def process_user_input(self, input):
        # parse user input string
        try:
            contact_data = yaml.load(input, Loader=yaml.BaseLoader)
        except yaml.parser.ParserError as e:
            raise ValueError(e)
        except yaml.scanner.ScannerError as e:
            raise ValueError(e)
        else:
            if contact_data is None:
                raise ValueError("Error: Found no contact information")

        # check for available data
        # at least enter name or organisation
        if not bool(contact_data.get("First name")) \
                and not bool(contact_data.get("Last name")) \
                and not bool(contact_data.get("Organisation")):
            raise ValueError(
                    "Error: You must either enter a name or an organisation")

        # delete vcard version
        # the correct version is added automatically on saving again
        self.delete_vcard_object("VERSION")

        # update rev
        self.delete_vcard_object("REV")
        self.add_rev(datetime.datetime.now())

        # name
        self.delete_vcard_object("FN")
        self.delete_vcard_object("N")
        # although the "n" attribute is not explisitely required by the vcard specification,
        # the vobject library throws an exception, if it doesn't exist
        # so add the name regardless if it's empty or not
        self.add_name(
                contact_data.get("Prefix") or "",
                contact_data.get("First name") or "",
                contact_data.get("Additional") or "",
                contact_data.get("Last name") or "",
                contact_data.get("Suffix") or "")
        # nickname
        self.delete_vcard_object("NICKNAME")
        if bool(contact_data.get("Nickname")):
            if isinstance(contact_data.get("Nickname"), str):
                self.add_nickname(contact_data.get("Nickname"))
            elif isinstance(contact_data.get("Nickname"), list):
                for nickname in contact_data.get("Nickname"):
                    if bool(nickname):
                        self.add_nickname(nickname)
            else:
                raise ValueError(
                        "Error: nickname must be a string or a list of strings")

        # organisation
        self.delete_vcard_object("ORG")
        self.delete_vcard_object("X-ABSHOWAS")
        if bool(contact_data.get("Organisation")):
            if isinstance(contact_data.get("Organisation"), str):
                self.add_organisation([contact_data.get("Organisation")])
            elif isinstance(contact_data.get("Organisation"), list):
                for organisation in contact_data.get("Organisation"):
                    if bool(organisation):
                        if isinstance(organisation, str):
                            self.add_organisation([organisation])
                        else:
                            self.add_organisation(organisation)
            else:
                raise ValueError(
                        "Error: organisation must be a string or a list of strings")

        # role
        self.delete_vcard_object("ROLE")
        if bool(contact_data.get("Role")):
            if isinstance(contact_data.get("Role"), str):
                self.add_role(contact_data.get("Role"))
            elif isinstance(contact_data.get("Role"), list):
                for role in contact_data.get("Role"):
                    if bool(role):
                        self.add_role(role)
            else:
                raise ValueError(
                        "Error: role must be a string or a list of strings")

        # title
        self.delete_vcard_object("TITLE")
        if bool(contact_data.get("Title")):
            if isinstance(contact_data.get("Title"), str):
                self.add_title(contact_data.get("Title"))
            elif isinstance(contact_data.get("Title"), list):
                for title in contact_data.get("Title"):
                    if bool(title):
                        self.add_title(title)
            else:
                raise ValueError(
                        "Error: title must be a string or a list of strings")

        # phone
        self.delete_vcard_object("TEL")
        if bool(contact_data.get("Phone")):
            if isinstance(contact_data.get("Phone"), dict):
                for type, number_list in contact_data.get("Phone").items():
                    if isinstance(number_list, list) \
                            or isinstance(number_list, str):
                        if isinstance(number_list, str):
                            number_list = [number_list]
                        for number in number_list:
                            if bool(number):
                                self.add_phone_number(type, number)
                    else:
                        raise ValueError(
                                "Error: got no number or list of numbers "
                                "for the phone number type " + type)
            else:
                raise ValueError(
                        "Error: missing type value for phone number field")

        # email
        self.delete_vcard_object("EMAIL")
        if bool(contact_data.get("Email")):
            if isinstance(contact_data.get("Email"), dict):
                for type, email_list in contact_data.get("Email").items():
                    if isinstance(email_list, list) \
                            or isinstance(email_list, str):
                        if isinstance(email_list, str):
                            email_list = [email_list]
                        for email in email_list:
                            if bool(email):
                                self.add_email_address(type, email)
                    else:
                        raise ValueError(
                                "Error: got no email or list of emails "
                                "for the email address type " + type)
            else:
                raise ValueError(
                        "Error: missing type value for email address field")

        # post addresses
        self.delete_vcard_object("ADR")
        if bool(contact_data.get("Address")):
            if isinstance(contact_data.get("Address"), dict):
                for type, post_adr_list in contact_data.get("Address").items():
                    if isinstance(post_adr_list, dict) \
                            or isinstance(post_adr_list, list):
                        if isinstance(post_adr_list, dict):
                            post_adr_list = [post_adr_list]
                        for post_adr in post_adr_list:
                            if isinstance(post_adr, dict):
                                address_not_empty = False
                                for key, value in post_adr.items():
                                    if key in [
                                                "Box", "Extended", "Street",
                                                "Code", "City", "Region",
                                                "Country"] \
                                            and bool(value):
                                        address_not_empty = True
                                        break
                                if address_not_empty:
                                    self.add_post_address(
                                            type,
                                            post_adr.get("Box") or "",
                                            post_adr.get("Extended") or "",
                                            post_adr.get("Street") or "",
                                            post_adr.get("Code") or "",
                                            post_adr.get("City") or "",
                                            post_adr.get("Region") or "",
                                            post_adr.get("Country") or "")
                            else:
                                raise ValueError(
                                        "Error: one of the " + type + " type "
                                        "address list items does not contain "
                                        "an address")
                    else:
                        raise ValueError(
                                "Error: got no address or list of addresses "
                                "for the post address type " + type)
            else:
                raise ValueError(
                        "Error: missing type value for post address field")

        # categories
        self.delete_vcard_object("CATEGORIES")
        if bool(contact_data.get("Categories")):
            if isinstance(contact_data.get("Categories"), str):
                self.add_category([contact_data.get("Categories")])
            elif isinstance(contact_data.get("Categories"), list):
                only_contains_strings = True
                for sub_category in contact_data.get("Categories"):
                    if not isinstance(sub_category, str):
                        only_contains_strings = False
                        break
                # if the category list only contains strings, pack all of them
                # in a single CATEGORIES vcard tag
                if only_contains_strings:
                    self.add_category(contact_data.get("Categories"))
                else:
                    for sub_category in contact_data.get("Categories"):
                        if bool(sub_category):
                            if isinstance(sub_category, str):
                                self.add_category([sub_category])
                            else:
                                self.add_category(sub_category)
            else:
                raise ValueError(
                        "Error: category must be a string or a list of strings")

        # jabber
        self.delete_vcard_object("X-JABBER")
        if bool(contact_data.get("Jabber")):
            if isinstance(contact_data.get("Jabber"), str):
                self.add_jabber_id(contact_data.get("Jabber"))
            elif isinstance(contact_data.get("Jabber"), list):
                for jabber_id in contact_data.get("Jabber"):
                    if bool(jabber_id):
                        self.add_jabber_id(jabber_id)
            else:
                raise ValueError(
                        "Error: jabber id must be a string or a list of strings")

        # skype
        self.delete_vcard_object("X-SKYPE")
        if bool(contact_data.get("Skype")):
            if isinstance(contact_data.get("Skype"), str):
                self.add_skype_id(contact_data.get("Skype"))
            elif isinstance(contact_data.get("Skype"), list):
                for skype_id in contact_data.get("Skype"):
                    if bool(skype_id):
                        self.add_skype_id(skype_id)
            else:
                raise ValueError(
                        "Error: skype id must be a string or a list of strings")

        # twitter
        self.delete_vcard_object("X-TWITTER")
        if bool(contact_data.get("Twitter")):
            if isinstance(contact_data.get("Twitter"), str):
                self.add_twitter_id(contact_data.get("Twitter"))
            elif isinstance(contact_data.get("Twitter"), list):
                for twitter_id in contact_data.get("Twitter"):
                    if bool(twitter_id):
                        self.add_twitter_id(twitter_id)
            else:
                raise ValueError(
                        "Error: twitter id must be a string or a list of strings")

        # urls
        self.delete_vcard_object("URL")
        if bool(contact_data.get("Webpage")):
            if isinstance(contact_data.get("Webpage"), str):
                self.add_webpage(contact_data.get("Webpage"))
            elif isinstance(contact_data.get("Webpage"), list):
                for webpage in contact_data.get("Webpage"):
                    if bool(webpage):
                        self.add_webpage(webpage)
            else:
                raise ValueError(
                        "Error: webpage must be a string or a list of strings")

        # birthday
        self.delete_vcard_object("BDAY")
        if bool(contact_data.get("Birthday")):
            if isinstance(contact_data.get("Birthday"), str):
                bday_date = None
                supported_date_formats = ["%d-%m-%Y", "%Y-%m-%d"]
                for date_format in supported_date_formats:
                    try:
                        bday_date = datetime.datetime.strptime(
                                re.sub("\D", "-", contact_data.get("Birthday")),
                                date_format)
                    except ValueError as e:
                        pass
                    else:
                        break
                if bday_date:
                    self.add_birthday(bday_date)
                else:
                    raise ValueError(
                            "Error: Wrong birthday date format\n"
                            "Examples: 21.10.1988, 1988.10.21 or 1988-10-21")
            else:
                raise ValueError("Error: birthday must be a string object.")

        # notes
        self.delete_vcard_object("NOTE")
        if bool(contact_data.get("Note")):
            if isinstance(contact_data.get("Note"), str):
                self.add_note(contact_data.get("Note"))
            elif isinstance(contact_data.get("Note"), list):
                for note in contact_data.get("Note"):
                    if bool(note):
                        self.add_note(note)
            else:
                raise ValueError(
                        "Error: note must be a string or a list of strings\n"
                        "Use the | character to create a multi-line note.")


    def get_template(self):
        strings = []
        for line in helpers.get_new_contact_template().splitlines():
            if line.startswith("#"):
                strings.append(line)
            elif line == "":
                strings.append(line)

            elif line.lower().startswith("prefix"):
                strings += helpers.convert_to_yaml(
                        "Prefix", self.get_name_prefixes(), 0, 11, True)
            elif line.lower().startswith("first name"):
                strings += helpers.convert_to_yaml(
                        "First name", self.get_first_names(), 0, 11, True)
            elif line.lower().startswith("additional"):
                strings += helpers.convert_to_yaml(
                        "Additional", self.get_additional_names(), 0, 11, True)
            elif line.lower().startswith("last name"):
                strings += helpers.convert_to_yaml(
                        "Last name", self.get_last_names(), 0, 11, True)
            elif line.lower().startswith("suffix"):
                strings += helpers.convert_to_yaml(
                        "Suffix", self.get_name_suffixes(), 0, 11, True)
            elif line.lower().startswith("nickname"):
                strings += helpers.convert_to_yaml(
                        "Nickname", self.get_nicknames(), 0, 11, True)

            elif line.lower().startswith("organisation"):
                strings += helpers.convert_to_yaml(
                        "Organisation", self.get_organisations(), 0, 13, True)
            elif line.lower().startswith("title"):
                strings += helpers.convert_to_yaml(
                        "Title", self.get_titles(), 0, 13, True)
            elif line.lower().startswith("role"):
                strings += helpers.convert_to_yaml(
                        "Role", self.get_roles(), 0, 13, True)

            elif line.lower().startswith("phone"):
                strings.append("Phone :")
                if len(self.get_phone_numbers().keys()) == 0:
                    strings.append("    cell : ")
                    strings.append("    home : ")
                else:
                    longest_key = max(self.get_phone_numbers().keys(), key=len)
                    for type, number_list in sorted(
                            self.get_phone_numbers().items(),
                            key=lambda k: k[0].lower()):
                        strings += helpers.convert_to_yaml(
                                type, number_list, 4, len(longest_key)+1, True)

            elif line.lower().startswith("email"):
                strings.append("Email :")
                if len(self.get_email_addresses().keys()) == 0:
                    strings.append("    home : ")
                    strings.append("    work : ")
                else:
                    longest_key = max(self.get_email_addresses().keys(), key=len)
                    for type, email_list in sorted(
                            self.get_email_addresses().items(),
                            key=lambda k: k[0].lower()):
                        strings += helpers.convert_to_yaml(
                                type, email_list, 4, len(longest_key)+1, True)

            elif line.lower().startswith("address"):
                strings.append("Address :")
                if len(self.get_post_addresses().keys()) == 0:
                    strings.append("    home :")
                    strings.append("        Box      : ")
                    strings.append("        Extended : ")
                    strings.append("        Street   : ")
                    strings.append("        Code     : ")
                    strings.append("        City     : ")
                    strings.append("        Region   : ")
                    strings.append("        Country  : ")
                else:
                    for type, post_adr_list in sorted(
                            self.get_post_addresses().items(),
                            key=lambda k: k[0].lower()):
                        strings.append("    %s:" % type)
                        for post_adr in post_adr_list:
                            indentation = 8
                            if len(post_adr_list) > 1:
                                indentation += 4
                                strings.append("        -")
                            strings += helpers.convert_to_yaml(
                                    "Box", post_adr.get("box"),
                                    indentation, 9, True)
                            strings += helpers.convert_to_yaml(
                                    "Extended", post_adr.get("extended"),
                                    indentation, 9, True)
                            strings += helpers.convert_to_yaml(
                                    "Street", post_adr.get("street"),
                                    indentation, 9, True)
                            strings += helpers.convert_to_yaml(
                                    "Code", post_adr.get("code"),
                                    indentation, 9, True)
                            strings += helpers.convert_to_yaml(
                                    "City", post_adr.get("city"),
                                    indentation, 9, True)
                            strings += helpers.convert_to_yaml(
                                    "Region", post_adr.get("region"),
                                    indentation, 9, True)
                            strings += helpers.convert_to_yaml(
                                    "Country", post_adr.get("country"),
                                    indentation, 9, True)

            elif line.lower().startswith("jabber"):
                strings += helpers.convert_to_yaml(
                        "Jabber", self.get_jabber_ids(), 0, 8, True)
            elif line.lower().startswith("skype"):
                strings += helpers.convert_to_yaml(
                        "Skype", self.get_skype_ids(), 0, 8, True)
            elif line.lower().startswith("twitter"):
                strings += helpers.convert_to_yaml(
                        "Twitter", self.get_twitter_ids(), 0, 8, True)
            elif line.lower().startswith("webpage"):
                strings += helpers.convert_to_yaml(
                        "Webpage", self.get_webpages(), 0, 8, True)

            elif line.lower().startswith("categories"):
                strings += helpers.convert_to_yaml(
                        "Categories", self.get_categories(), 0, 11, True)
            elif line.lower().startswith("birthday"):
                date = self.get_birthday()
                if not date:
                    strings.append("Birthday : ")
                else:
                    strings.append("Birthday : %.2d.%.2d.%.4d" % (date.day, date.month, date.year))
            elif line.lower().startswith("note"):
                strings += helpers.convert_to_yaml(
                        "Note", self.get_notes(), 0, 5, True)
        return '\n'.join(strings)

    def print_vcard(self, show_address_book = True, show_uid = True):
        strings = []
        # name
        if self.get_first_names() or self.get_last_names():
            names = []
            if self.get_name_prefixes():
                names += self.get_name_prefixes()
            if self.get_first_names():
                names += self.get_first_names()
            if self.get_additional_names():
                names += self.get_additional_names()
            if self.get_last_names():
                names += self.get_last_names()
            if self.get_name_suffixes():
                names += self.get_name_suffixes()
            strings.append("Name: %s" % helpers.list_to_string(names, " "))
        # organisation
        if len(self.get_organisations()) > 0:
            if len(self.get_organisations()) == 1:
                strings.append("Organisation: %s"
                        % helpers.list_to_string(
                            self.get_organisations(), ", "))
            else:
                strings.append("Organisations:")
                for organisation in self.get_organisations():
                    strings.append("    - %s"
                            % helpers.list_to_string(organisation, ", "))

        # person related information
        if self.get_birthday() != None \
                or len(self.get_nicknames()) > 0 \
                or len(self.get_roles()) > 0 \
                or len(self.get_titles()) > 0:
            strings.append("General:")
            if self.get_birthday():
                date = self.get_birthday()
                strings.append("    Birthday: %.2d.%.2d.%.4d" % (date.day, date.month, date.year))
            if len(self.get_nicknames()) > 0:
                strings += helpers.convert_to_yaml(
                        "Nickname", self.get_nicknames(), 4, -1, False)
            if len(self.get_roles()) > 0:
                strings += helpers.convert_to_yaml(
                        "Role", self.get_roles(), 4, -1, False)
            if len(self.get_titles()) > 0:
                strings += helpers.convert_to_yaml(
                        "Title", self.get_titles(), 4, -1, False)

        # phone numbers
        if len(self.get_phone_numbers().keys()) > 0:
            strings.append("Phone")
            for type, number_list in sorted(
                    self.get_phone_numbers().items(), key=lambda k: k[0].lower()):
                strings += helpers.convert_to_yaml(
                        type, number_list, 4, -1, False)

        # email addresses
        if len(self.get_email_addresses().keys()) > 0:
            strings.append("E-Mail")
            for type, email_list in sorted(
                    self.get_email_addresses().items(),
                    key=lambda k: k[0].lower()):
                strings += helpers.convert_to_yaml(
                        type, email_list, 4, -1, False)

        # post addresses
        if len(self.get_post_addresses().keys()) > 0:
            strings.append("Address")
            for type, post_adr_list in sorted(
                    self.get_formatted_post_addresses().items(),
                    key=lambda k: k[0].lower()):
                strings += helpers.convert_to_yaml(
                        type, post_adr_list, 4, -1, False)

        # im and webpages
        if len(self.get_jabber_ids()) > 0 \
                or len(self.get_skype_ids()) > 0 \
                or len(self.get_twitter_ids()) > 0 \
                or len(self.get_webpages()) > 0:
            strings.append("Instant messaging and social networks")
            if len(self.get_jabber_ids()) > 0:
                strings += helpers.convert_to_yaml(
                        "Jabber", self.get_jabber_ids(), 4, -1, False)
            if len(self.get_skype_ids()) > 0:
                strings += helpers.convert_to_yaml(
                        "Skype", self.get_skype_ids(), 4, -1, False)
            if len(self.get_twitter_ids()) > 0:
                strings += helpers.convert_to_yaml(
                        "Twitter", self.get_twitter_ids(), 4, -1, False)
            if len(self.get_webpages()) > 0:
                strings += helpers.convert_to_yaml(
                        "Webpage", self.get_webpages(), 4, -1, False)

        # misc stuff
        if show_address_book \
                or len(self.get_categories()) > 0 \
                or len(self.get_notes()) > 0 \
                or (show_uid and self.get_uid() != ""):
            strings.append("Miscellaneous")
            if show_address_book:
                strings.append("    Address book: %s" % self.address_book.get_name())
            if len(self.get_categories()) > 0:
                strings += helpers.convert_to_yaml(
                        "Categories", self.get_categories(), 4, -1, False)
                #if len(self.get_categories()) == 1:
                #    strings.append("    Categories: %s"
                #            % helpers.list_to_string(
                #                self.get_categories(), ", "))
                #else:
                #    strings.append("    Categories:")
                #    for sub_category in self.get_categories():
                #        strings.append("        - %s"
                #                % helpers.list_to_string(sub_category, ", "))
            if len(self.get_notes()) > 0:
                strings += helpers.convert_to_yaml(
                        "Note", self.get_notes(), 4, -1, False)
            if show_uid and self.get_uid():
                strings.append("    UID: %s" % self.get_uid())
        return '\n'.join(strings)


    def write_to_file(self, overwrite=False):
        try:
            with atomic_write(self.filename, overwrite=overwrite) as f:
                f.write(self.vcard.serialize())
        except vobject.base.ValidateError as e:
            print("Error: Vcard is not valid.\n%s" % e)
            sys.exit(4)
        except IOError as e:
            print("Error: Can't write\n%s" % e)
            sys.exit(4)
        except OSError as e:
            print("Error: vcard with the file name %s already exists\n%s" \
                    % (os.path.basename(self.filename), e))
            sys.exit(4)

    def delete_vcard_object(self, object_name):
        # first collect all vcard items, which should be removed
        to_be_removed = []
        for child in self.vcard.getChildren():
            if child.name == object_name:
                if child.group:
                    for label in self.vcard.getChildren():
                        if label.name == "X-ABLABEL" and label.group == child.group:
                            to_be_removed.append(label)
                to_be_removed.append(child)
        # then delete them one by one
        for item in to_be_removed:
            self.vcard.remove(item)

    def delete_vcard_file(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)
        else:
            print("Error: Vcard file %s does not exist." % self.filename)
            sys.exit(4)


    #######################
    # static helper methods
    #######################

    def get_types_for_vcard_object(self, object, default_type):
        """
        get list of types for phone number, email or post address
        :param object: vcard class object
        :type object: vobject.vCard
        :param default_type: use if the object contains no type
        :type default_type: str
        :returns: list of type labels
        :rtype: list(str)
        """
        type_list = []
        # try to find label group for custom value type
        if object.group:
            for label in self.vcard.getChildren():
                if label.name == "X-ABLABEL" and label.group == object.group:
                    custom_type = label.value.strip()
                    if custom_type:
                        type_list.append(custom_type)
        # then load type from params dict
        standard_types = object.params.get("TYPE")
        if standard_types is not None:
            if not isinstance(standard_types, list):
                standard_types = [standard_types]
            for type in standard_types:
                type = type.strip()
                if type:
                    if not type.lower().startswith("x-"):
                        type_list.append(type)
                    elif type[2:] not in type_list:
                        # add x-custom type in case it's not already added by
                        # custom label for loop above but strip x- before
                        type_list.append(type[2:])
        if type_list:
            return type_list
        return [default_type]

    def parse_type_value(self, types, value, supported_types):
        """ parse type value of phone numbers, email and post addresses
        :param types: list of type values
        :type types: list(str)
        :param value: the corresponding label, required for more verbose exceptions
        :type value: str
        :param supported_types: all allowed standard types
        :type supported_types: list(str)
        :returns: tuple of standard and custom types
        :rtype: tuple(list(str), list(str))
        """
        custom_types = []
        standard_types = []
        for type in types:
            type = type.strip()
            if type:
                if type.lower() in supported_types:
                    standard_types.append(type)
                else:
                    if type.lower().startswith("x-"):
                        custom_types.append(type[2:])
                        standard_types.append(type)
                    else:
                        custom_types.append(type)
                        standard_types.append("X-%s" % type)
        return (standard_types, custom_types)

