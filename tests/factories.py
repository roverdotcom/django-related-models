from __future__ import unicode_literals

import factory

from tests.test_app_1.models import Person
from tests.test_app_1.models import PersonLocation
from tests.test_app_1.models import Pet
from tests.test_app_2.models import TaggedItem


class PersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Person

    first_name = factory.Sequence(lambda n: '\xd3scarNumber{}'.format(n))
    last_name = factory.Sequence(lambda n: 'Ib\xe1\xf1ezNumber{}'.format(n))


class PetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Pet

    name = factory.Sequence(lambda n: 'Buddy{}'.format(n))
    owner = factory.SubFactory(PersonFactory)


class PersonLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PersonLocation

    address1 = factory.Sequence(lambda n: 'Middle of Nowhere.')
    address2 = factory.Sequence(lambda n: 'No number, obviously.')
    owner = factory.SubFactory(PersonFactory)


class TaggedItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TaggedItem
