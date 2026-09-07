from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("learning", "0006_javascript_access")]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="position",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Orden didáctico dentro del módulo; 0 para actividades sin orden definido.",
            ),
        ),
        migrations.AlterModelOptions(
            name="activity",
            options={"ordering": ("module", "position", "title")},
        ),
    ]
