from django.contrib.gis.db import models
from django.contrib.auth.models import AbstractUser

# --------------------------
# Modelo Custom User (Granjero)
# --------------------------
class CustomUser(AbstractUser):
    # Hereda campos básicos: username, email, password, etc.
    farms = models.ManyToManyField('Farm', related_name='farmers', blank=True)
    
    def __str__(self):
        return self.email

# --------------------------
# Modelo Granja (Farm)
# --------------------------
class Farm(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='owned_farms')
    name = models.CharField(max_length=200)
    location = models.PointField(srid=4326)  # Coordenadas WGS84 (lat/lon)
    total_area = models.FloatField(null=True, blank=True)  # Calculado automáticamente
    created_at = models.DateTimeField(auto_now_add=True)

    def update_total_area(self):
        """Actualiza el área total sumando las parcelas"""
        self.total_area = self.plots.aggregate(models.Sum('area'))['area__sum']
        self.save()

    def __str__(self):
        return f"{self.name} ({self.owner.email})"

# --------------------------
# Modelo Parcela (Plot)
# --------------------------
#soil_type y crop_type deben ser tablas tambien
class Plot(models.Model):
    SOIL_TYPES = [
        ('clay', 'Arcilloso'),
        ('sandy', 'Arenoso'),
        ('loamy', 'Limoso'),
    ]
    
    CROP_TYPES = [
        ('corn', 'Maíz'),
        ('wheat', 'Trigo'),
        ('soy', 'Soja'),
    ]

    id = models.UUIDField(primary_key=True, editable=False)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='plots')
    name = models.CharField(max_length=200)
    perimeter = models.PolygonField(srid=4326)  # Polígono en WGS84
    area = models.FloatField(editable=False)  # Calculado con PostGIS
    soil_type = models.CharField(max_length=50, choices=SOIL_TYPES)
    crop_type = models.CharField(max_length=50, choices=CROP_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Calcula el área usando PostGIS antes de guardar
        self.area = self.perimeter.area  # ST_Area en PostGIS
        super().save(*args, **kwargs)
        self.farm.update_total_area()  # Actualiza el área total de la granja

    def __str__(self):
        return f"{self.name} | {self.get_crop_type_display()}"

# --------------------------
# Modelo Sensor
# --------------------------
class Sensor(models.Model):
    SENSOR_TYPES = [
        ('temperature', 'Temperatura'),
        ('humidity', 'Humedad del Suelo'),
        ('ph', 'pH'),
        ('light', 'Luminosidad'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Activo'),
        ('inactive', 'Inactivo'),
        ('maintenance', 'Mantenimiento'),
    ]

    id = models.UUIDField(primary_key=True, editable=False)
    plot = models.ForeignKey(Plot, on_delete=models.CASCADE, related_name='sensors')
    type = models.CharField(max_length=50, choices=SENSOR_TYPES)
    model = models.CharField(max_length=100)
    last_calibration = models.DateTimeField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"{self.get_type_display()} ({self.plot.name})"

# --------------------------
# Modelo Medición
# --------------------------
class Measurement(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='measurements')
    value = models.FloatField()
    unit = models.CharField(max_length=20) # Ej: '°C', '%', 'pH', 'lx'
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sensor.type}: {self.value}{self.unit}"
