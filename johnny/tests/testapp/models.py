#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Test models for Johnny-Cache"""

import django
from django.db import models
from django.db.models import permalink
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

def get_urlfield(*args, **kwargs):
    if django.VERSION >= 1.4 and 'verify_exists' in kwargs:
        del kwargs['verify_exists']
        return models.URLField(*args, **kwargs)
    return models.URLField(*args, **kwargs)


#from basic.people.models import Person

class Issue24Model(models.Model):
    one = models.PositiveIntegerField()
    two = models.PositiveIntegerField()

class User(models.Model):
    """User model."""
    first_name = models.CharField('first name', blank=True, max_length=128)
    last_name = models.CharField('last name', blank=True, max_length=128)
    username = models.CharField('username', blank=True, max_length=128)

    def __repr__(self):
        return '<User: %s %s>' % (self.first_name, self.last_name)

class PersonType(models.Model):
    """Person type model."""
    title = models.CharField(_('title'), max_length=100)
    slug = models.SlugField(_('slug'), unique=True)

    class Meta:
        verbose_name = _('person type')
        verbose_name_plural = _('person types')
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('person_type_detail', None, {'slug': self.slug})

# some details left out of the Person model, in order to avoid a requirement
# on python-dateutil

class Person(models.Model):
    """Person model."""
    GENDER_CHOICES = (
        (1, 'Male'),
        (2, 'Female'),
    )
    user = models.ForeignKey(User, blank=True, null=True)
    first_name = models.CharField(_('first name'), blank=True, max_length=100)
    middle_name = models.CharField(_('middle name'), blank=True, max_length=100)
    last_name = models.CharField(_('last name'), blank=True, max_length=100)
    slug = models.SlugField(_('slug'), unique=True)
    gender = models.PositiveSmallIntegerField(_('gender'), choices=GENDER_CHOICES, blank=True, null=True)
    mugshot = models.FileField(_('mugshot'), upload_to='mugshots', blank=True)
    mugshot_credit = models.CharField(_('mugshot credit'), blank=True, max_length=200)
    birth_date = models.DateField(_('birth date'), blank=True, null=True)
    person_types = models.ManyToManyField(PersonType, blank=True)
    website = get_urlfield(_('website'), blank=True, verify_exists=True)

    class Meta:
        verbose_name = _('person')
        verbose_name_plural = _('people')
        ordering = ('last_name', 'first_name',)

    def __unicode__(self):
        return u'%s' % self.full_name

    @property
    def full_name(self):
        return u'%s %s' % (self.first_name, self.last_name)

    @permalink
    def get_absolute_url(self):
        return ('person_detail', None, {'slug': self.slug})


class Genre(models.Model):
    """Genre model"""
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('book_genre_detail', None, { 'slug': self.slug })


class Publisher(models.Model):
    """Publisher"""
    title = models.CharField(max_length=100)
    prefix = models.CharField(max_length=20, blank=True)
    slug = models.SlugField(unique=True)
    website = get_urlfield(blank=True, verify_exists=False)

    class Meta:
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.full_title

    @property
    def full_title(self):
        return '%s %s' % (self.prefix, self.title)

    @permalink
    def get_absolute_url(self):
        return ('book_publisher_detail', None, { 'slug':self.slug })


class Book(models.Model):
    """Listing of books"""
    title = models.CharField(max_length=255)
    prefix = models.CharField(max_length=20, blank=True)
    subtitle = models.CharField(blank=True, max_length=255)
    slug = models.SlugField(unique=True)
    authors = models.ManyToManyField(Person, limit_choices_to={'person_types__slug__exact': 'author'}, related_name='books')
    isbn = models.CharField(max_length=14, blank=True)
    pages = models.PositiveSmallIntegerField(blank=True, null=True, default=0)
    publisher = models.ForeignKey(Publisher, blank=True, null=True)
    published = models.DateField(blank=True, null=True)
    cover = models.FileField(upload_to='books', blank=True)
    description = models.TextField(blank=True)
    genre = models.ManyToManyField(Genre, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('title',)

    def __unicode__(self):
        return '%s' % self.full_title

    @property
    def full_title(self):
        if self.prefix:
            return '%s %s' % (self.prefix, self.title)
        else:
            return '%s' % self.title

    @permalink
    def get_absolute_url(self):
        return ('book_detail', None, { 'slug': self.slug })

    @property
    def amazon_url(self):
        if self.isbn:
            try:
                return 'http://www.amazon.com/dp/%s/?%s' % (self.isbn, settings.AMAZON_AFFILIATE_EXTENTION)
            except:
                return 'http://www.amazon.com/dp/%s/' % self.isbn
        return ''


class Highlight(models.Model):
    """Highlights from books"""
    user = models.ForeignKey(User)
    book = models.ForeignKey(Book)
    highlight = models.TextField()
    page = models.CharField(blank=True, max_length=20)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '%s' % self.highlight

    @permalink
    def get_absolute_url(self):
        return ('book_detail', None, { 'slug': self.book.slug })

class Page(models.Model):
    """Page model"""
    user = models.ForeignKey(User)
    book = models.ForeignKey(Book)
    current_page = models.PositiveSmallIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created',)

    def __unicode__(self):
        return '%s' % self.current_page

class Milk(models.Model):
    """A meaningless model designed to test unicode ability.  This might screw
    up databases that can't handle unicode table/column names."""
    name = models.CharField(blank=True, max_length=20, db_column=u'名前')
    chocolate = models.BooleanField(blank=True, db_column=u'チョコレート')

    class Meta:
        db_table = u'ミルク'



