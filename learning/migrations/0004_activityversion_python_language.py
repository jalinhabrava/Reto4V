from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0003_activityversion_bash_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activityversion",
            name="language",
            field=models.CharField(
                choices=[
                    ("web", "HTML/CSS/JavaScript"),
                    ("bash", "Bash"),
                    ("python", "Python"),
                ],
                default="web",
                max_length=20,
            ),
        ),
    ]
