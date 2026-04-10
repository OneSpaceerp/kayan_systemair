SELECT 
    nominal_diameter as "Nominal Diameter (mm):Int:180", 
    min_weight_kg as "Min Weight (kg):Float:150", 
    max_weight_kg as "Max Weight (kg):Float:150"
FROM 
    `tabSystemAir Weight Table`
ORDER BY 
    nominal_diameter ASC
