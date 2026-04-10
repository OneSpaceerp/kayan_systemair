SELECT 
    i.item_code as "Item Code:Link/Item:150", 
    i.item_name as "Item Name:Data:250", 
    i.sa_product_family as "Product Group:Data:150", 
    ipg.price_list_rate as "Germany Price (EUR):Currency:140", 
    ipm.price_list_rate as "Malaysia Price (EUR):Currency:140", 
    i.sa_primary_factory as "Factory:Data:120", 
    i.modified as "Last Updated:Date:120"
FROM 
    `tabItem` i
LEFT JOIN 
    `tabItem Price` ipg ON i.name = ipg.item_code AND ipg.price_list = 'Systemair Germany 2026'
LEFT JOIN 
    `tabItem Price` ipm ON i.name = ipm.item_code AND ipm.price_list = 'Systemair Malaysia 2026'
WHERE 
    i.item_group = 'SystemAir Axial Fans'
ORDER BY 
    i.item_code ASC
