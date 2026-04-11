SELECT
    nominal_diameter AS `Nominal Diameter (mm)`,
    min_weight_kg    AS `Min Weight (kg)`,
    max_weight_kg    AS `Max Weight (kg)`
FROM `tabSystemAir Weight Table`
ORDER BY nominal_diameter ASC
