import csv
import random

voltages = ["0.6/1kV", "1.1/2kV", "0.6/0.9kV", "3.3kV", "6.6kV"]
insulations = ["PVC", "XLPE", "EPR"]
core_counts = [1, 2, 3, 4, 5, 7]
cross_sections = [0.5, 1.0, 1.5, 2.5, 4.0, 6.0, 10.0, 16.0]
armors = ["Steel", "Aluminum", "None", "Copper"]
standards = ["IS 1554", "IS 7098", "IEC 60502", "BS 5467", "IEEE 1202"]

conductor_materials = ["Copper", "Aluminum"]

min_price = 40
max_price = 500

num_products = 200

with open("dummy_cable_catalog_extended.csv", mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow([
        "sku", "product_name", "voltage", "insulation", "core_count",
        "cross_section_mm2", "armor", "standard", "conductor_material", "base_price"
    ])

    for i in range(1, num_products + 1):
        voltage = random.choice(voltages)
        insulation = random.choice(insulations)
        core_count = random.choice(core_counts)
        cross_section = random.choice(cross_sections)
        armor = random.choice(armors)
        standard = random.choice(standards)
        conductor = random.choice(conductor_materials)
        # Price influenced slightly by cross section and conductor
        price_base = round(random.uniform(min_price, max_price), 2)
        price_modifier = cross_section * (1.5 if conductor == "Copper" else 1.0)
        base_price = round(price_base * price_modifier / 10, 2)

        sku = f"CAB_{i:04d}"
        product_name = (f"{core_count}-core {cross_section}mm² {insulation} "
                        f"Insulated {armor} Armored Cable ({conductor})")

        writer.writerow([
            sku, product_name, voltage, insulation, core_count,
            cross_section, armor, standard, conductor, base_price
        ])

print("Generated => dummy_cable_catalog_extended.csv")
