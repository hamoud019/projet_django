from django.db import models

class Asset(models.Model):
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=50)
    category = models.CharField(
        max_length=20,
        choices=[
            ("fx", "Devise"),
            ("metal", "Métal"),
            ("crypto", "Crypto"),
        ],
    )

    def __str__(self):
        return self.code


class Price(models.Model):
    SOURCE_CHOICES = [
        ("bcm", "API Banque Centrale Mauritanie"),
        ("api", "API Externe"),
        ("sim", "Simulation"),
        ("init", "Données Initiales"),
    ]
    
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    date = models.DateField()
    price_mru = models.DecimalField(max_digits=14, decimal_places=4)
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="api",
        help_text="Source de la donnée de prix"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "date"],
                name="unique_asset_date"
            )
        ]

    def __str__(self):
        return f"{self.asset.code} {self.date}"
