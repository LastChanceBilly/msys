"""
Models

The classes defined here are essential to Django's ORM magic

"""

import datetime
from django.db import models
from django.forms import ModelForm
from django.forms import Select, SelectMultiple, TextInput
from django.forms import DateInput, NumberInput, TimeInput
from django.forms import CheckboxSelectMultiple, Textarea

from .stripe_handler import director

class MemberType(models.Model):
    """
    For users to define custom types of members. Perhaps Staff or Guests...
    """
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class MemberCard(models.Model):
    """
    Obsolete -- See AccessCard

    TODO: remove
    """
    start_date = models.DateField()
    expire_date = models.DateField()

class Member(models.Model):
    """
    A member of the org.

    Members can be associated with one or more memberships.

    In general, all the important info about each member is contained in this class.
    """
    number = models.IntegerField()
    type = models.ForeignKey(MemberType, models.PROTECT)

    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    birth_date = models.DateField()
    first_seen_date = models.DateField()
    last_seen_date = models.DateField()

    address = models.CharField(max_length=200)
    city = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=200)

    phone_number = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    emergency_contact = models.CharField(max_length=200)
    emergency_phone_number = models.CharField(max_length=200)

    stripe_customer_code = models.CharField(max_length=200, null=True, blank=True)

    brief_notes = models.CharField(max_length=200, null=True, blank=True)

    @property
    def get_cache(self):
        if(self.has_cache == False):
            return self.create_cache
        else:
            return Member_stripe_cache.objects.get(member=self)

    @property
    def has_cache(self):
        cache_old = Member_stripe_cache.objects.filter(member=self)
        if(len(cache_old)> 0):
            return True
        else:
            return False

    @property
    def create_cache(self):
        """
        Creates a new Member stripe cache object, after looking for previous entries
        and eliminating them.
        """
        cache_old = Member_stripe_cache.objects.filter(member=self)
        for cache in cache_old:
            """
            TO DO: Output previous entries records on txt files as backups
            """
            cache.delete()
        cache = Member_stripe_cache(member=self)
        cache.get_update
        cache.save()
        return cache

    def has_active_membership(self):
        """
        Check to see if the Member has an active Membership

        Returns True if there is at least one Membership associated with the Member
        that has not yet expired.
        """
        m_ships = Membership.objects.filter(member=self.pk)

        for ship in m_ships:
            if ship.is_active():
                return True

        return False

    def __str__(self):
        return self.first_name + " " + self.last_name

class Member_stripe_cache(models.Model):
    """
    Stores a local cache of a member's stripe information

    Contains it's own maintenance functions, but requires at least a member object
    to use as a reference.
    """
    member = models.ForeignKey(Member, models.PROTECT)

    account_balance = models.CharField(max_length=200, default=' ')
    created = models.DateField(default=datetime.date.today)
    
    delinquent = models.BooleanField(default=False)
    description = models.CharField(max_length=200, default=' ')
    #discount = models.CharField(max_length=200)
    
    email = models.CharField(max_length=200, default=' ')
    sources = models.CharField(max_length=400, default=' ')

    raw = models.TextField(default=' ')

    index = ['account_balance', 'created', 'delinquent', 'description', 'email', 'sources', 'raw']

    @property
    def get_balance_numeric_value(self):
        """
        Returns numeric value of account_balance
        """
        numeric = int(float(self.account_balance)*100)*0.1
        return numeric

    @property
    def is_up_to_date(self):
        """
        Compares local cache information with stripe's database.
        (Note: While it'll be nice to have said functionality, but if a whole JSON will have
        to be requested anyways, it becomes rather pointless. Either way, I could probably go back 
        and find a better way later on)
        """
        handler = director.stripe_handler()
        customer = handler.get_customer_object(self.member.stripe_customer_code)
        if(customer):
            return self.raw == customer
        else:
            return False

    @property
    def get_update(self):
        """
        Update this individual instance of the class. 
        (Note: Also all membership caches related to the self.member object)
        """
        print(self.raw)
        handler = director.stripe_handler()
        customer = handler.get_customer_object(self.member.stripe_customer_code)
        stripe_data = self.update(customer)
        #print(stripe_data)
        if(stripe_data):
            """
            Maybe a bad implementation. I just didn't know how to pass the dictionary as
            arguments without creating a new instance
            """
            self.account_balance = stripe_data['account_balance']
            self.created = stripe_data['created']
            self.delinquent = stripe_data['delinquent']
            self.description = stripe_data['description']
            self.email = stripe_data['email']
            self.sources = stripe_data['sources']
            self.raw = stripe_data['raw']
            Membership_stripe_cache.update(self.member, self.raw)
            return 1
        else:
            return 0

    @classmethod
    def update_all(cls):
        """
        Update all instances of this class.
        (Note: Also all membership caches related to the self.member object)
        """
        class_items = cls.objects.all()
        handler = director.stripe_handler()
        customer = handler.get_customer_object(cls.member.stripe_customer_code)
        stripe_data = cls.update(customer)
        if(stripe_data):
            """
            Maybe a bad implementation. I just didn't know how to pass the dictionary as
            arguments without creating a new instance.
            (Note: Maybe it'll be a lot faster just calling get_update for all members on a 
            for loop?)
            """
            cls.account_balance = stripe_data['account_balanc']
            cls.created = stripe_data['created']
            cls.delinquent = stripe_data['delinquent']
            cls.description = stripe_data['description']
            cls.email = stripe_data['email']
            cls.sources = stripe_data['sources']
            cls.raw = stripe_data['raw']
            Membership_stripe_cache.update(cls.member, cls.raw)
            return 1
        else:
            return 0

    def update(self, customer):
        """
        Gets a direct stripe update on the customer's information and querys it for the model.
        """
        index = self.index
        stripe_data = {}
        if(customer):
            for i in index:
                if(i == 'created'):
                    stripe_data[i] = datetime.datetime.fromtimestamp(int(customer[i])).strftime('%Y-%m-%d')
                elif(i == 'delinquent'):
                    stripe_data[i] = customer[i] == "true"
                elif(i == 'sources'):
                    srcs = customer['sources'].data
                    if(len(srcs) > 0):
                        for items in srcs:
                            stripe_data['sources'] += item + "\n"
                    else:
                        stripe_data['sources'] = " "
                elif(i == 'raw'):
                    stripe_data[i] = customer
                else:
                    stripe_data[i] = customer[i]
            return stripe_data
        else:
            return 0   

    def __str__(self):
        return self.raw

class Membership(models.Model):
    """
    Class representing a membership contract.

    One member may have a history of expired memberships in the database.
    """
    member = models.ForeignKey(Member, models.PROTECT)
    start_date = models.DateField()
    expire_date = models.DateField()

    stripe_subscription_code = models.CharField(max_length=200, null=True, blank=True)

    def is_active(self):
        """
        Check if the membership has expired or not

        Returns True if the membership start date is earlier than the current date and
        the membership end date is in the future.
        """
        today = datetime.date.today()
        if self.start_date <= today and self.expire_date > today:
            return True

        return False

    def __str__(self):
        ret = str(self.member) + ": " + str(self.start_date) + " to " + str(self.expire_date)

        if self.expire_date < datetime.date.today():
            ret += ' (expired)'
        else:
            delta = self.expire_date - datetime.date.today()
            ret += ' (' + str(delta.days) + ' remaining)'

        return ret

class Membership_stripe_cache(models.Model):
    member = models.ForeignKey(Member, models.PROTECT)
    stripe_customer_code = models.CharField(max_length=200, default=' ')

    subs_name = models.CharField(max_length=200, default=' ')
    sub_id = models.CharField(max_length=200, default=' ')

    billing = models.CharField(max_length=200, default=' ')

    created = models.DateField(default=datetime.date.today)
    cancel_at_period_end = models.BooleanField(default=False)

    current_period_end = models.DateField(default=datetime.date.today)
    current_period_start = models.DateField(default=datetime.date.today)

    #subs_description = models.CharField(max_length=200, default=' ')

    @staticmethod
    def update(member, customer):
        
        sub_i = {}
        sub_i['stripe_customer_code'] = customer.stripe_customer_code
        sub_i['member'] = member

        subs = customer.subscriptions
        if(len(subs.data)):
            for data in subs.data:
                #dd = data dictionary
                dd = data.to_dict()

                sub_i['sub_id'] =dd['id']
                sub_i['billing'] = dd['billing']
                sub_i['created'] = datetime.datetime.fromtimestamp(int(dd['created'])).strftime('%Y-%m-%d')
                sub_i['cancel_at_period_end'] = dd['cancel_at_period_end']
                sub_i['current_period_end'] = datetime.datetime.fromtimestamp(int(dd['current_period_end'])).strftime('%Y-%m-%d')
                sub_i['current_period_start'] = datetime.datetime.fromtimestamp(int(dd['current_period_start'])).strftime('%Y-%m-%d')
                sub_i['subs_name'] = data.to_dict()['items']['data'][0].to_dict()['plan']['name']

                sub_new = Membership_stripe_cache(**sub_i)

                sub_old = Membership_stripe_cache.objects.filter(stripe_customer_code=sub_new.stripe_customer_code, sub_id=sub_new.sub_id)
                for sub in sub_old:
                    sub.delete()
                sub_new.save()





class Promotion(models.Model):
    """
    Class representing a type or classification of promotion that was offered.
    """

    name = models.CharField(max_length=200)
    quantity = models.IntegerField()

    def __str__(self):
        return str(self.name)

class Promo_item(models.Model):
    """
    Class representing the a "coupon" or some kind of promotional item. It could be
    a one time membership, special status, or multiple use tickets.
    """

    promo = models.ForeignKey(Promotion, models.PROTECT)
    member = models.ForeignKey(Member, models.PROTECT)
    used = models.IntegerField()
    total = models.IntegerField()

    def __str__(self):
        ret = "promo: {} ({}) {}/{}".format(self.promo, self.member, self.used, self.total)
        return ret

class Promo_sub(models.Model):
    """
    Class to indicate which memberships are created from or associated with promotions
    """

    promo = models.ForeignKey(Promotion, models.PROTECT)
    membership = models.ForeignKey(Membership, models.PROTECT)

    def __str__(self):
        ret = "{} <-> {}".format(self.promo, self.membership)
        return ret

class AccessCard(models.Model):
    """
    Class representing the card (RFID or unique token) that Members may have

    Members may have one or more AccessCards.

    AccessCards can be associated with AccessGroups for providing access at groups of times.
    """
    member = models.ForeignKey(Member, models.PROTECT)
    unique_id = models.CharField(max_length=30)

    def numeric(self):
        """Returns a numeric representation of the unique id associated with the object"""
        byte_list = self.unique_id.split()
        num = 0
        for b_byte in byte_list:
            num = num << 8
            num = num + int(b_byte, base=16)

        return num

    def has_access_now(self):
        """Simplified wrapper for has_access_at_time(...)"""
        return self.has_access_at_time(datetime.datetime.now().date(),
                                       datetime.datetime.now().time())

    def has_access_at_time(self, date, time):
        """
        Check if this card grants access at a given date and time

        Params:
        date -- a datetime.date object representing the date to check
        time -- a datetime.time object representing the time to check

        TODO: consider simplifying the parameters
        """
        day2day = {'mon': 0,
                   'tues': 1,
                   'wed': 2,
                   'thurs': 3,
                   'fri': 4,
                   'sat': 5,
                   'sun': 6
                  }#Todo: this code should not be replicated in more than one place!!
        #get a list of AGs linked to this card
        ag_set = self.accessgroup_set.all()
        for agroup in ag_set:
            #now get the TBs linked to the AG
            tb_set = TimeBlock.objects.filter(group=agroup)
            for tblock in tb_set:
                if date.weekday() == day2day[tblock.day] and time >= tblock.start and time <= tblock.end:
                    return True
                else:
                    continue
        return False



    def __str__(self):
        ret = self.unique_id
        ret += ' (' + str(self.member) + ')'
        return ret

class AccessGroup(models.Model):
    """
    AccessGroups are a many-to-many relationship between AccessCards and TimeBlocks
    """
    name = models.CharField(max_length=200)
    card = models.ManyToManyField(AccessCard, null=True, blank=True)

    def __str__(self):
        return str(self.name)

class TimeBlock(models.Model):
    """
    Represents a block of time during the week.

    TimeBlocks are not aware of specific calendar dates. Instead this class represents a
    weekday and time that will come and go each week.
    """
    DAY_CHOICES = (
        ('mon', 'Monday'),
        ('tues', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thurs', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    )
    day = models.CharField(max_length=8,
                           choices=DAY_CHOICES,
                           default='sat')
    start = models.TimeField(default=datetime.time.min)
    end = models.TimeField(default=datetime.time.max)
    group = models.ForeignKey(AccessGroup, models.PROTECT)

    def __str__(self):
        return '{} from {} to {}'.format(self.day, self.start, self.end)

class AccessBlock(models.Model):
    """
    OBSOLETE -- See AccessGroup and TimeBlock

    TODO: remove
    """
    DAY_CHOICES = (
        ('mon', 'Monday'),
        ('tues', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thurs', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
        ('all', 'Every Day'),
    )

    member = models.ForeignKey(Member, models.PROTECT)
    day = models.CharField(max_length=8,
                           choices=DAY_CHOICES,
                           default='sat')
    start = models.TimeField(default=datetime.time.min)
    end = models.TimeField(default=datetime.time.max)

    def __str__(self):
        ret = self.day + ' from ' + str(self.start) + ' to ' + str(self.end)
        ret += ' (' + str(self.member) + ')'
        return ret

############### Logs #############

class LogEvent(models.Model):
    """
    Record of a change made to the system
    """

    date = models.DateField()
    time = models.TimeField()
    text = models.TextField()

    @staticmethod
    def log_now(txt):

        log = LogEvent()
        log.date = datetime.date.today()
        log.time = datetime.datetime.now().time()

        log.text = txt
        log.save()

    def __str__(self):
        ret = "{} {} || {}".format(self.date, self.time, self.text)
        return ret


class LogAccessRequest(models.Model):
    """
    Record of access requests made to the system
    """
    date = models.DateField()
    time = models.TimeField()
    text = models.TextField()

    @staticmethod
    def log_now(txt):

        log = LogAccessRequest()
        log.date = datetime.date.today()
        log.time = datetime.datetime.now().time()

        log.text = txt
        log.save()

    def __str__(self):
        ret = "{} {} || {}".format(self.date, self.time, self.text)
        return ret

class LogCardLogin(models.Model):
    """
    Record of logins perform by the members
    """
    date = models.DateField()
    time = models.TimeField()
    text = models.TextField()

    @staticmethod
    def log_now(txt):
        log = LogCardLogin()
        log.date = datetime.date.today()
        log.time = datetime.datetime.now().time()

        log.text = txt
        log.save()
    
    def __str__(self):
        ret = "{} {} || {}".format(self.date, self.time, self.text)
        return ret


############### Reports #############

class IncidentReport(models.Model):
    """
    Report of an incident that occured.
    """

    post_date = models.DateField()
    post_time = models.TimeField()

    report_date = models.DateField()
    report_time = models.TimeField()

    effected_members = models.ManyToManyField(Member, related_name="incident_effected")
    staff_on_duty = models.ManyToManyField(Member, related_name="incident_witness")

    description = models.TextField()
    damage = models.TextField()
    root_cause = models.TextField()
    mitigation = models.TextField()
    actions_taken = models.TextField()
    actions_todo = models.TextField()

    def __str__(self):
        simple_time = str(self.post_time).split('.')[0]
        ret = "Incident Report: {} {}".format(self.post_date, simple_time)
        return ret;

class IncidentReportForm(ModelForm):
    class Meta:
        model = IncidentReport
        fields = ['report_date', 'report_time', 'effected_members', 'staff_on_duty',
                  'description', 'damage', 'root_cause', 'mitigation', 'actions_taken', 'actions_todo']

        labels = {
            'report_date': 'Date when the incident happened:',
            'report_time': 'Time when incident occured (HH:MM:SS):',
            'effected_members': 'Select the members who were involved in the incident (select multiple):',
            'staff_on_duty': 'Select the staff members on duty at the time (select multiple):',
            'description': 'Briefly describe the incident:',
            'damage': 'List any/all resulting injury or damage:',
            'root_cause': 'Describe what factors lead to this incident. Why doesn\'t it normally happen?',
            'mitigation': 'What can be done to prevent this kind of incident:',
            'actions_taken': 'What actions were taken in responce to this incident:',
            'actions_todo': 'What actions still need to be done:',
        }

        widgets = {'report_date': DateInput(attrs={'class': 'form-control datepicker'}),
                   'report_time': TimeInput(attrs={'class': 'form-control timepicker'}),
                   'effected_members': SelectMultiple(attrs={'class': 'form-control selectpicker',
                                                             'data-style': 'btn-primary'}),
                   'staff_on_duty': SelectMultiple(attrs={'class': 'form-control selectpicker',
                                                          'data-style': 'btn-primary'}),
                   'description': Textarea(attrs={'class': 'form-control'}),
                   'damage': Textarea(attrs={'class': 'form-control'}),
                   'root_cause': Textarea(attrs={'class': 'form-control'}),
                   'mitigation': Textarea(attrs={'class': 'form-control'}),
                   'actions_taken': Textarea(attrs={'class': 'form-control'}),
                   'actions_todo': Textarea(attrs={'class': 'form-control'}),
        }

############### Forms #############

class MemberForm(ModelForm):
    class Meta:
        model = Member
        fields = ['type', 'first_name', 'last_name',
                  'birth_date', 'address', 'city',
                  'postal_code', 'phone_number', 'email',
                  'emergency_contact', 'emergency_phone_number',
                  'stripe_customer_code', 'brief_notes']
        labels = {
            'birth_date': 'Birthdate (MM/DD/YYYY)',
            'stripe_customer_code': 'Stripe customer code (Leave blank if none)',
            'brief_notes': 'Notes (keep it brief - 200 characters max)'
        }

        widgets = {'type': Select(attrs={'class': 'form-control'}),
                   'first_name': TextInput(attrs={'class': 'form-control'}),
                   'last_name': TextInput(attrs={'class': 'form-control'}),
                   'birth_date': DateInput(attrs={'class': 'form-control datepicker'}),
                   'address': TextInput(attrs={'class': 'form-control'}),
                   'city': TextInput(attrs={'class': 'form-control'}),
                   'postal_code': TextInput(attrs={'class': 'form-control'}),
                   'phone_number': TextInput(attrs={'class': 'form-control'}),
                   'email': TextInput(attrs={'class': 'form-control'}),
                   'emergency_contact': TextInput(attrs={'class': 'form-control'}),
                   'emergency_phone_number': TextInput(attrs={'class': 'form-control'}),
                   'stripe_customer_code': TextInput(attrs={'class': 'form-control'}),
                   'brief_notes': TextInput(attrs={'class': 'form-control'}),
        }

class MembershipForm(ModelForm):
    class Meta:
        model = Membership
        fields = ['member',
                  'start_date', 'expire_date',
                  'stripe_subscription_code']
        widgets = {'member': Select(attrs={'class': 'form-control'}),
                   'start_date': DateInput(attrs={'class': 'form-control datepicker'}),
                   'expire_date': DateInput(attrs={'class': 'form-control datepicker'}),
                   'stripe_subscription_code': TextInput(attrs={'class': 'form-control'}),
                  }
        labels = {'start_date': 'Start Date (MM/DD/YYYY):',
                  'expire_date': 'Expire Date (MM/DD/YYYY):',
                }

class PromoForm(ModelForm):
    class Meta:
        model = Promotion
        fields = ['name', 'quantity']
        widgets = {'name': TextInput(attrs={'class': 'form-control'}),
                   'quantity': NumberInput(attrs={'class': 'form-control'}), }

class PromoItemForm(ModelForm):
    class Meta:
        model = Promo_item
        fields = ['promo', 'member', 'used', 'total']
        widgets = {'promo': Select(attrs={'class': 'form-control'}),
                   'member': Select(attrs={'class': 'form-control'}),
                   'used': NumberInput(attrs={'class': 'form-control'}),
                   'total': NumberInput(attrs={'class': 'form-control'})}

class CardForm(ModelForm):
    class Meta:
        model = AccessCard
        fields = ['member',
                  'unique_id']
        widgets = {'member': Select(attrs={'class': 'form-control'}),
                   'unique_id': TextInput(attrs={'class': 'form-control'}),}

class BlockForm(ModelForm):
    class Meta:
        model = AccessBlock
        fields = ['member',
                  'day',
                  'start',
                  'end']
