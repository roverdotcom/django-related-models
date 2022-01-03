import abc

from django.test import TestCase

from django_related_models.related_models import FieldPreimage
from django_related_models.related_models import RelatedModels
from django_related_models.related_models import get_related_objects
from django_related_models.related_models import get_related_objects_mapping
from tests.factories import PersonFactory
from tests.factories import PersonLocationFactory
from tests.factories import PetFactory
from tests.factories import TaggedItemFactory
from tests.test_app_1.models import Person
from tests.test_app_1.models import PersonLocation
from tests.test_app_1.models import Pet
from tests.test_app_2.models import TaggedItem


class GetRelatedObjectsMappingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super(GetRelatedObjectsMappingTests, cls).setUpTestData()
        cls.person = PersonFactory.create()

    def test_get_related_objects_custom_related_models(self):
        rm = RelatedModels(exclude={Pet})
        PetFactory.create_batch(3, owner=self.person)
        self.assertEqual(
            rm.get_related_objects_mapping(self.person),
            {}
        )

    def test_get_related_fk_objects(self):
        pets = PetFactory.create_batch(3, owner=self.person)
        location = PersonLocationFactory.create(owner=self.person)

        self.assertEqual(
            get_related_objects_mapping(self.person),
            {
                Pet.owner.field: set(pets),
                PersonLocation.owner.field: {location}
            }
        )

    def test_get_related_generic_fk_objects(self):
        tagged_item = TaggedItemFactory.create(
            tag='dog-person',
            content_object=self.person
        )
        self.assertEqual(
            get_related_objects_mapping(self.person),
            {
                TaggedItem.content_object: {tagged_item}
            }
        )


class GetRelatedObjectsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super(GetRelatedObjectsTests, cls).setUpTestData()
        cls.person = PersonFactory.create()

    def test_get_related_objects_custom_related_models(self):
        rm = RelatedModels(exclude={Pet})
        PetFactory.create_batch(3, owner=self.person)
        self.assertEqual(
            set(rm.get_related_objects(self.person)),
            set()
        )

    def test_get_related_fk_objects(self):
        pets = PetFactory.create_batch(3, owner=self.person)
        location = PersonLocationFactory.create(owner=self.person)

        self.assertEqual(
            set(get_related_objects(self.person)),
            set(pets) | {location}
        )

    def test_get_related_generic_fk_objects(self):
        tagged_item = TaggedItemFactory.create(
            tag='dog-person',
            content_object=self.person
        )
        self.assertEqual(
            set(get_related_objects(self.person)),
            {tagged_item}
        )


class FieldPreimageTestsMixin(object):
    __metaclass__ = abc.ABCMeta

    @classmethod
    def setUpTestData(cls):
        super(FieldPreimageTestsMixin, cls).setUpTestData()
        cls.instance = PersonFactory.create()

    def setUp(self):
        super().setUp()
        self.field = self.get_field()
        self.field_preimage = self.get_field_preimage()

    def get_field_preimage(self, **kwargs):
        kwargs = dict({
            'target_model': type(self.instance),
            'field': self.field,
        }, **kwargs)
        return FieldPreimage(**kwargs)

    @abc.abstractmethod
    def get_field(cls):
        """
        Returns the default field to use for :class:`FieldPreimage`.

        :rtype: :class:`django.db.models.fields.Field

        """


class FieldPreimageTests(FieldPreimageTestsMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super(FieldPreimageTests, cls).setUpTestData()
        cls.pet = PetFactory.create(owner=cls.instance)

    def get_field(self):
        return Pet._meta.get_field('owner')

    def test_field(self):
        self.assertEqual(self.field_preimage.field, self.field)

    def test_model(self):
        self.assertEqual(self.field_preimage.model, Pet)

    def test_generic_foreign_key(self):
        self.assertIsNone(self.field_preimage.generic_foreign_key)

    def test_get_related_objects(self):
        new_pet = PetFactory.create(owner=self.instance)
        self.assertEqual(
            list(self.field_preimage.get_related_objects(self.instance)),
            [self.pet, new_pet]
        )

    def test_get_related_objects_extra_kwargs(self):
        new_pet = PetFactory.create(owner=self.instance)
        self.assertEqual(
            list(self.field_preimage.get_related_objects(self.instance, pk=new_pet.pk)),
            [new_pet]
        )


class FieldPreimageGenericForeignKeyTests(FieldPreimageTestsMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super(FieldPreimageGenericForeignKeyTests, cls).setUpTestData()
        cls.tagged_item = TaggedItemFactory.create(
            tag='dog-person',
            content_object=cls.instance
        )

    def get_field(self):
        return TaggedItem._meta.get_field('content_object')

    def test_field(self):
        self.assertEqual(
            self.field_preimage.field,
            TaggedItem._meta.get_field('object_id')
        )

    def test_model(self):
        self.assertEqual(self.field_preimage.model, TaggedItem)

    def test_generic_foreign_key(self):
        self.assertEqual(self.field_preimage.generic_foreign_key, self.field)

    def test_get_related_objects(self):
        self.assertEqual(
            list(self.field_preimage.get_related_objects(self.instance)),
            [self.tagged_item]
        )

    def test_get_related_objects_extra_kwargs(self):
        tagged_item = TaggedItemFactory.create(
            tag='cat-person',
            content_object=self.instance
        )
        self.assertEqual(
            list(self.field_preimage.get_related_objects(self.instance, pk=tagged_item.pk)),
            [tagged_item]
        )


class RelatedModelsTests(TestCase):
    def setUp(self):
        super(RelatedModelsTests, self).setUp()
        self.related_models = RelatedModels()

    def test_should_consider(self):
        self.assertTrue(self.related_models.should_consider(Pet))

    def test_should_consider_excluded_model(self):
        rm = RelatedModels(exclude=[Pet])
        self.assertFalse(rm.should_consider(Pet))

    def test_should_consider_excluded_app(self):
        rm = RelatedModels(exclude_apps=[Pet._meta.app_label])
        self.assertFalse(rm.should_consider(Pet))

    def test_should_consider_included_app_true(self):
        rm = RelatedModels(include_apps=[Pet._meta.app_label])
        self.assertTrue(rm.should_consider(Pet))

    def test_should_consider_included_app_false(self):
        rm = RelatedModels(include_apps=[Pet._meta.app_label])
        self.assertFalse(rm.should_consider(TaggedItem))

    def test_has_generic_foreign_key_to_model_false(self):
        self.assertFalse(
            self.related_models.has_generic_foreign_key_to_model(
                TaggedItem.content_object,
                Person
            )
        )

    def test_has_generic_foreign_key_to_model_true(self):
        TaggedItemFactory.create(
            content_object=PersonFactory.create(),
            tag='dog-person',
        )
        self.assertTrue(
            self.related_models.has_generic_foreign_key_to_model(
                TaggedItem.content_object,
                Person
            )
        )

    def test_has_generic_foreign_key_to_model_true_cached(self):
        TaggedItemFactory.create(
            content_object=PersonFactory.create(),
            tag='dog-person',
        )
        self.related_models.has_generic_foreign_key_to_model(
            TaggedItem.content_object,
            Person
        )
        with self.assertNumQueries(0):
            self.assertTrue(
                self.related_models.has_generic_foreign_key_to_model(
                    TaggedItem.content_object,
                    Person
                )
            )
