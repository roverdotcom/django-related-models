"""
Implement a way to, given an instance, fetch all its related models and their associated data.

Classes:
========
    GetDefaultManagerMixin
    FieldPreimage
    RelatedModels

Functions:
==========
    get_related_objects
    get_related_objects_mapping

Miscellaneous objects:
======================
    Except the above, all other objects in this module are to be considered implementation details.
"""

import itertools

from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class GetDefaultManagerMixin(object):
    """
    A mixin which provides a method to get a default manager for
    a given model.  This is useful if the normal ":attr:`objects`" manager
    associated to that class has some built-in filtering.
    """
    def get_default_manager(self, model):
        """
        Returns a default manager for *model*.

        :rtype: :class:`django.db.models.manager.Manager`
        """
        return model._default_manager


class FieldPreimage(GetDefaultManagerMixin, object):
    """
    This purpose of this class is to hold information and provide
    utility functions about getting all instances where *field* is
    a foreign key to an instance of *target_model*.

    The :attr:`model` is the model associated to *field*.

    The :attr:`target_field` attribute is the field on the type
    of :attr:`instance`.


    This class also abstracts away some of the difference between
    normal foreign keys and generic foreign keys.  In the case of a
    generic foreign key, :attr:`generic_foreign_key` will be set to that
    field, :attr:`field` will be the concrete "object id" field, and
    :attr:`target_field` will be the primary key on :attr:`target_model`.
    """

    def __init__(self, target_model, field):
        if isinstance(field, GenericForeignKey):
            # For generic foreign keys, fk_field is the name of the
            # field which needs to be updated and the target field
            # will be the primary key of *model*
            self.generic_foreign_key = field
            self.field = field.model._meta.get_field(field.fk_field)
            self.target_field = target_model._meta.pk
        else:
            self.generic_foreign_key = None
            self.field = field
            self.target_field = field.target_field

        self.model = self.field.model
        self.target_model = self.target_field.model
        assert self.target_model == target_model

    def get_default_manager(self, model=None):
        """
        Returns a default manager for *model*.  If *model* is ``None``,
        then it will return a default manager for :attr:`model`, which
        is the same as :attr:`field.model`.

        :rtype: :class:`django.db.models.manager.Manager`
        """
        model = model or self.model
        return super(FieldPreimage, self).get_default_manager(model)

    def get_related_objects(self, instance, **kwargs):
        """
        Returns a :class:`~django.db.models.QuerySet` for :attr:`model`
        for the rows that are associated to *instance*.

        Any *kwargs* passed in will be additional filters applied to the
        queryset.

        :type instance: :attr:`model`
        :rtype: :class:`django.db.models.QuerySet`
        """
        # If we have a generic foreign key, we need to additionally
        # filter by the content type of the target model
        if self.generic_foreign_key is not None:
            content_type = ContentType.objects.get_for_model(self.target_model)
            kwargs = dict({
                self.generic_foreign_key.ct_field: content_type
            }, **kwargs)

        kwargs = dict({
            self.field.name: getattr(instance, self.target_field.name)
        }, **kwargs)
        return self.get_default_manager().filter(**kwargs)


class RelatedModels(GetDefaultManagerMixin, object):
    """
    This class is designed to help finding all of the other models
    related to a given model.
    """
    def __init__(
            self,
            include=None,
            include_apps=None,
            exclude=None,
            exclude_apps=None):
        self.include = include
        self.include_apps = include_apps
        self.exclude = set(exclude or [])
        self.exclude_apps = set(exclude_apps or [])
        self.generic_foreign_key_cache = {}

    def _model_matches(self, model, model_list, app_list):
        """
        Returns whether or not *model* appears in *model_list* or it's app
        appears in *app_list*.

        :rtype: bool
        """
        if model_list is not None and model in model_list:
            return True
        if app_list is not None and model._meta.app_label in app_list:
            return True
        return False

    def should_consider(self, other_model):
        """
        Returns whether or not we should consider the fields on
        *other_model*.

        :rtype: bool
        """
        if self._model_matches(other_model, self.exclude, self.exclude_apps):
            return False

        if self._model_matches(other_model, self.include, self.include_apps):
            return True

        return self.include is None and self.include_apps is None

    def should_include_field(self, field, model):
        """
        Returns whether or not *field* is (or should be considered) as a
        a foreign key to *model*.

        :rtype: bool
        """
        if isinstance(field, GenericForeignKey):
            return self.has_generic_foreign_key_to_model(field, model)

        return (
            model == getattr(field, 'related_model', None) and
            field.concrete and
            not field.many_to_many
        )

    def has_generic_foreign_key_to_model(self, field, model):
        """
        Returns whether or not the generic foreign key *field* has any
        references to *model*.

        We cache the content types which are referenced by *field*
        into :attr:`generic_foreign_key_cache`.

        :rtype: bool
        """
        content_type_ids = self.generic_foreign_key_cache.get(field)
        if content_type_ids is None:
            content_type_ids = set(
                self.get_default_manager(field.model).values_list(
                    field.ct_field,
                    flat=True
                ).order_by().distinct()
            )
            self.generic_foreign_key_cache[field] = content_type_ids

        if not content_type_ids:
            return False

        ct = ContentType.objects.get_for_model(model)
        return ct.id in content_type_ids

    def get_related_fields(self, model, other_model):
        """
        Returns all of the fields on *other_model* which are (or could be)
        foreign keys to *model*.

        :type model: :class:`django.db.models.Model`
        :type other_model: :class:`django.db.models.Model`

        :rtype: List[Field]
        """

        all_fields = itertools.chain(
            other_model._meta.get_fields(),
            getattr(other_model._meta, 'private_fields', [])
        )
        return [
            field for field in all_fields
            if self.should_include_field(field, model)
        ]

    def get_referring_models(self, model):
        """
        Returns all of the models which have a (possibly generic)foreign key to
        *model*.

        :rtype: Dict[Model, List[Field]]
        """
        referring_models = {
            other_model: self.get_related_fields(model, other_model)
            for other_model in apps.get_models(include_auto_created=True)
            if self.should_consider(other_model)
        }
        return {
            other_model: fields
            for other_model, fields in referring_models.items()
            if fields
        }

    def _get_related_objects_iterator(self, instance):
        """
        An iterator for internal use which yields a tuple of a field
        and an object related to *instance* via that field.
        """
        model = instance._meta.model
        referring_models = self.get_referring_models(model)

        for fields in referring_models.values():
            for field in fields:
                objects_map = FieldPreimage(type(instance), field)
                related_objects = objects_map.get_related_objects(instance)
                for obj in related_objects.iterator():
                    yield field, obj

    def get_related_objects_mapping(self, instance):
        """
        Returns an dictionary mapping fields to a set of the objects related to
        *instance* via that field.

        :rtype: Dict[Field, List[Object]]
        """
        groups = itertools.groupby(
            self._get_related_objects_iterator(instance),
            key=lambda pair: pair[0]
        )
        return {
            field: set(obj for field, obj in pairs)
            for field, pairs in groups
        }

    def get_related_objects(self, instance):
        """
        Returns an iterator for all of the of all the models which have a
        (possibly generic) foreign key to *instance*.

        :rtype: Iterator[object]
        """
        for _, obj in self._get_related_objects_iterator(instance):
            yield obj


def get_related_objects(instance):
    """
    Returns an iterator for all of the of all the models which have a
    (possibly generic) foreign key to *instance*.

    :rtype: Iterator[object]
    """
    return RelatedModels().get_related_objects(instance)


def get_related_objects_mapping(instance):
    """
    Returns an dictionary mapping fields to a set of the objects related to
    *instance* via that field.

    :rtype: Dict[Field, List[Object]]
    """
    return RelatedModels().get_related_objects_mapping(instance)
