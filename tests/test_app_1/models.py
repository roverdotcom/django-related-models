from django.db import models


class Person(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)


class Pet(models.Model):
    name = models.CharField(max_length=30)
    owner = models.ForeignKey(
        Person, related_name="pets", on_delete=models.CASCADE, db_constraint=False
    )


class PersonLocation(models.Model):
    address1 = models.CharField(max_length=200)
    address2 = models.CharField(max_length=200)
    owner = models.ForeignKey(
        Person, related_name="owned_locations", on_delete=models.CASCADE, db_constraint=False
    )
