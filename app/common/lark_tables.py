from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FieldRef:
    id: str
    name: str


@dataclass
class TableDef:
    id: str
    name: str
    fields: dict[str, FieldRef] = field(default_factory=dict)

    def f(self, field_name: str) -> str:
        return self.fields[field_name].id


class _Tables:
    APP_TOKEN = "WXcubLU2oaJbHdsNTzCjy16Spwc"

    md_warehouse_address = TableDef(
        id="tblDpXM58OER6hfB",
        name="MD-Warehouse Address",
        fields={
            "address": FieldRef("fldeRIMBK8", "Address"),
            "location": FieldRef("fldRr562iz", "Location"),
            "detail": FieldRef("fldQ9O7Css", "Detail"),
            "warehouse_consingee": FieldRef("fldjB8FoUz", "Warehouse - Consingee"),
            "suburb": FieldRef("fldojSDXDC", "Suburb"),
            "warehouse_deliver": FieldRef("fldPmvRA6x", "Warehouse - Deliver"),
        },
    )

    md_warehouse_deliver_config = TableDef(
        id="tblIQSNhABhut1u7",
        name="MD-Warehouse Deliver Config",
        fields={
            "deliver_config": FieldRef("flddigHLS5", "Deliver Config"),
            "close_time": FieldRef("fldjNRfUQX", "Close Time"),
            "max_containers": FieldRef("fldU9ijRp5", "Max Containers"),
            "warehouse_address": FieldRef("fldEvH6hri", "Warehouse Address"),
            "op_cartage": FieldRef("fldx2pMQi3", "Op-Cartage"),
            "note": FieldRef("fldA6xX2tq", "Note"),
            "deliver_type": FieldRef("fldwwo9J0s", "Deliver Type"),
            "door_position": FieldRef("fldGZsmW9E", "Door Postion"),
            "open_time": FieldRef("fldxaT3rvQ", "Open Time"),
            "unload_time": FieldRef("fldYjEaz0l", "Unload Time (hrs)"),
        },
    )

    md_consingee = TableDef(
        id="tbli30rPlY5X5KT5",
        name="MD-Consingee",
        fields={
            "name": FieldRef("fldh6HjK3w", "Name"),
            "contact": FieldRef("fldLyNRRYJ", "Contact"),
            "phone": FieldRef("fldBL5YT8a", "Phone"),
            "email": FieldRef("fldoYFP8mA", "Email"),
            "warehouse_address": FieldRef("fldYhNuA8T", "MD-Warehouse Address"),
            "op_cartage": FieldRef("fldGDvCrOH", "Op-Cartage"),
            "sub_carrier_box_rate": FieldRef("fldfKF2fhF", "MD-Sub Carrier Box Rate"),
        },
    )

    md_suburb = TableDef(
        id="tbljmXaiKavx3Ycn",
        name="MD-Suburb",
        fields={
            "suburb": FieldRef("fldFAGgWp4", "Suburb"),
            "rural_tailgate": FieldRef("fldPZy0fQX", "Rural Tailgate"),
            "location": FieldRef("fldGPeg1Is", "Location"),
            "warehouse_suburb": FieldRef("fldHLLSeFV", "Warhouese-Suburb"),
            "state": FieldRef("fldcUuIdD2", "State"),
            "postcode": FieldRef("fldSl2vJYd", "Postcode"),
        },
    )

    md_base_node = TableDef(
        id="tblxITA0SwQpePBr",
        name="MD-Base Node",
        fields={
            "base_node": FieldRef("fldmQRwfru", "Base Node"),
            "location": FieldRef("fldiznncCb", "Location"),
            "type": FieldRef("fldx08udm6", "Type"),
            "terminal_base_node": FieldRef("fldIkRLvug", "MD-Terminal-Base Node"),
            "state": FieldRef("fldObmNt4B", "State"),
        },
    )

    md_distance_matrix = TableDef(
        id="tblurjC2qmgFmXFz",
        name="MD-Distance Matrix",
        fields={
            "suburb": FieldRef("fld4S8eLil", "Suburb"),
            "toll_code": FieldRef("fldgHozaVt", "Toll Code"),
            "time": FieldRef("fldbLv8hnX", "Time"),
            "base_node": FieldRef("fldol38k85", "Base Node"),
            "distance": FieldRef("fldybqIy1w", "Distance"),
            "index": FieldRef("fldSCeYREE", "Index"),
        },
    )

    md_vehicle = TableDef(
        id="tblgc1OZ7ZFrCBNt",
        name="MD-Vehicle",
        fields={
            "rego_number": FieldRef("fldlbcPxv2", "Rego Number"),
            "status": FieldRef("fld4j7vQPA", "Status"),
            "fuel_card": FieldRef("fldlz5shqP", "Fuel Card"),
            "depot": FieldRef("fldIWaTdr7", "Depot"),
            "expiry_date": FieldRef("fldPqMjxYv", "Expiry Date"),
            "owner": FieldRef("fldGq6agDX", "Owner"),
            "date_checked": FieldRef("fldeCqvFs5", "Date Checked"),
            "bat_number": FieldRef("fldQXjGfTE", "Bat Number"),
            "vehicle_class": FieldRef("fld70WI3ll", "Vehicle Class"),
            "driver_vehicle": FieldRef("fld6oOk4jJ", "MD-Driver-Vehicle"),
            "vehicle_type": FieldRef("fldQcToIZJ", "Vehicle Type"),
            "tag_number": FieldRef("fldzIKhSrh", "Tag Number"),
        },
    )

    md_driver = TableDef(
        id="tblzxHN8llzAf2ge",
        name="MD-Driver",
        fields={
            "driver_name": FieldRef("fldlP3B9Ra", "Driver Name"),
            "driver_config": FieldRef("fld71MnBz5", "MD-Driver Config-Driver"),
            "fuel_arrangement": FieldRef("fldUFiDobo", "Fuel Arrangement"),
            "status": FieldRef("fldGPrLPxS", "Status"),
            "depot": FieldRef("fldDW5jlUg", "Depot"),
            "msic_card": FieldRef("fldjML1CsU", "MSIC Card"),
            "driver_type": FieldRef("fldBET4nrG", "Driver Type"),
            "vehicle": FieldRef("fldTLXital", "Vehicle"),
            "msic_expiry": FieldRef("fldY0S0FqJ", "MSIC Expiry"),
            "contractor": FieldRef("fldbpWM42q", "Contractor"),
            "group_type": FieldRef("fldAtIhoBF", "Group Type"),
        },
    )

    md_driver_config = TableDef(
        id="tblnYYrqNM7Gact9",
        name="MD-Driver Config",
        fields={
            "note": FieldRef("fldqKpsp69", "Note"),
            "fuel_surcharge": FieldRef("fldMBPBtS6", "Fuel Surcharge"),
            "deduction": FieldRef("fldCVPtY9i", "Deduction"),
            "truck_type": FieldRef("fldzupbSzL", "Truck Type"),
            "driver_skill_pay": FieldRef("fldPrKv8eb", "Driver Skill Pay"),
            "labour_type": FieldRef("fld5hMOCzI", "Labour Type"),
            "labour_rate": FieldRef("fldMm40ccV", "Labour Rate"),
            "is_primary": FieldRef("fldm9BDQ76", "Is Primary"),
            "driver": FieldRef("fldidVFlmj", "Driver"),
        },
    )

    md_contractor = TableDef(
        id="tblsS9OXQG5LrbGk",
        name="MD-Contractor",
        fields={
            "account_number": FieldRef("fldIxdDzXt", "Account Number"),
            "driver_contractor": FieldRef("fldGCEvaEr", "MD-Driver-Contractor"),
            "abn_number": FieldRef("fld5ykUWDM", "ABN Number"),
            "bsb_number": FieldRef("flda7WwLFA", "BSB Number"),
            "payment_term": FieldRef("fldDfrqXg5", "Payment Term"),
            "sub_carrier": FieldRef("fldtrMNvbD", "MD-Sub Carrier"),
            "company_name": FieldRef("fldOXBUmwq", "Company Name"),
            "account_name": FieldRef("fldVVKM4rs", "Account Name"),
        },
    )

    md_sub_carrier = TableDef(
        id="tblfaVZfljmbzYka",
        name="MD-Sub Carrier",
        fields={
            "company_name": FieldRef("fldwWyFCW7", "Company Name"),
            "email_address": FieldRef("fldyrqQ0KF", "Email Address"),
            "sub_carrier_box_rate": FieldRef("fldYRaNpXY", "MD-Sub Carrier Box Rate"),
            "sub_carrier": FieldRef("fldppgHUat", "Sub Carrier"),
        },
    )

    md_sub_carrier_box_rate = TableDef(
        id="tbleewWnrNbAklTj",
        name="MD-Sub Carrier Box Rate",
        fields={
            "consingee_name": FieldRef("fldYCYARpD", "Consingnee Name"),
            "sub_carrier_box_config": FieldRef("fldMKz5JGG", "Sub Carrier Box Config"),
            "op_cartage": FieldRef("fldM3GUlH2", "Op-Cartage"),
            "deliver_config": FieldRef("fldepMA6mu", "Deliver Config"),
            "sub_carrier": FieldRef("fld2QaF592", "Sub Carrier"),
        },
    )

    md_shipping_line = TableDef(
        id="tblDcwZBZzMdIA0b",
        name="MD-Shipping Line",
        fields={
            "shipping_line": FieldRef("fldT5fHbm9", "Shipping Line"),
            "short_name": FieldRef("flddldvs5p", "Shiiping Line Short Name"),
            "op_import": FieldRef("fldbX5hT9o", "Op-Import"),
            "op_export": FieldRef("fldICnuNum", "Op-Export"),
        },
    )

    md_empty_park = TableDef(
        id="tblpyqsI8mFtV1nO",
        name="MD-Empty Park",
        fields={
            "empty_park": FieldRef("fldwLEHVad", "Empty Park"),
            "facility_address": FieldRef("fld4upbQuY", "Facility Address"),
            "alias": FieldRef("fldNWhSkie", "Alias"),
        },
    )

    md_terminal = TableDef(
        id="tblmR6o4iDakZT3H",
        name="MD-Terminal",
        fields={
            "terminal_cost": FieldRef("fldWIGZ3Nv", "MD-Terminal Cost-Terminal"),
            "base_node": FieldRef("fldRG7chiz", "Base Node"),
            "port_of_discharge": FieldRef("fldZmfzyoq", "Port of Discharge"),
            "terminal_fine": FieldRef("fldq1X7gZw", "MD-Terminal Fine-Terminal"),
            "op_vessel_schedule": FieldRef("fldjWiIRAJ", "Op-Vessel Schedule"),
            "is_code": FieldRef("fldrzmnjFC", "IS CODE"),
            "depot": FieldRef("fldJnjjsLr", "Depot"),
            "terminal_name": FieldRef("fldWOEA7TT", "Terminal Name"),
            "terminal_full_name": FieldRef("fldNV9ZpCm", "Terminal Full Name"),
        },
    )

    md_terminal_cost = TableDef(
        id="tblKDcsGemKgDNLb",
        name="MD-Terminal Cost",
        fields={
            "cost_description": FieldRef("fldhwKq1al", "Cost Despretion"),
            "amount": FieldRef("fld7nJJ5uH", "Amount"),
            "terminal": FieldRef("fld44UOxLr", "Terminal"),
            "cost_type": FieldRef("fldcuARUiK", "Cost Type"),
        },
    )

    md_terminal_fine = TableDef(
        id="tblwwKiGyef3hfF4",
        name="MD-Terminal Fine",
        fields={
            "fine_description": FieldRef("fldNz8Wapp", "Fine Desprection"),
            "amount": FieldRef("fldgVwugup", "Amount"),
            "terminal": FieldRef("fldFKWKc7K", "Terminal"),
            "scene": FieldRef("fldp9iTPe9", "Scene"),
            "fine_type": FieldRef("fldjbPDzH3", "Fine Type"),
        },
    )

    md_freight_forwarder = TableDef(
        id="tbloEdmaeYAp4D1s",
        name="MD-Freight Forwarder",
        fields={
            "price_level_nsw": FieldRef("fldvwAuxSz", "MD-Price Level(NSW)"),
            "ff_contact": FieldRef("fldy7ThCOb", "MD-FF Contact-Freight Forwarder"),
            "credit_limit": FieldRef("fldBiiTpUD", "Credit Limit"),
            "credit_term": FieldRef("fldhPWecGa", "Credit Term"),
            "name": FieldRef("fldY8wXdfc", "Name"),
            "note": FieldRef("fldhbFbIDw", "Note"),
            "price_level_vic": FieldRef("fldWpsH6AV", "MD-Price Level(VIC)"),
            "code": FieldRef("fldCzKy2ED", "Code"),
            "status": FieldRef("fld1cC78Ej", "Status"),
        },
    )

    md_ff_contact = TableDef(
        id="tbl2hIFHr8BeqkmU",
        name="MD-FF Contact",
        fields={
            "phone": FieldRef("fldQ13KUkL", "Phone"),
            "is_primary": FieldRef("fldh0mZ1BS", "Is Primary"),
            "freight_forwarder": FieldRef("fldmJHTVMF", "Freight Forwarder"),
            "email_address": FieldRef("fldvfwjTyS", "Email Address"),
            "tags": FieldRef("fld95wfcRn", "Tags"),
            "contact_person": FieldRef("fldlpIknZ9", "Contact Person"),
            "op_cartage": FieldRef("fldqyqO6wm", "Op-Cartage"),
            "position": FieldRef("fldRCoZkcT", "Position"),
        },
    )

    md_price_level = TableDef(
        id="tblVxSiE6t2grOuf",
        name="MD-Price Level",
        fields={
            "price_terminal": FieldRef("fldyeoOY8U", "MD-Price Terminal-Price Level"),
            "price_extra": FieldRef("fldrzqYvLf", "MD-Price Extra-Price Level"),
            "description": FieldRef("fldgPC93xL", "Description"),
            "state": FieldRef("fld06He8OC", "State"),
            "price_cartage": FieldRef("fld9brtZ2t", "MD-Price Cartage-Price Level"),
            "freight_forwarder": FieldRef("flds8xd3T1", "MD-Freight Forwarder-Price Level"),
            "dg_rate": FieldRef("fldjhCh7Dm", "DG Rate"),
            "fuel_rate": FieldRef("fld1nNADoS", "Fuel Rate"),
            "freight_forwarder_link": FieldRef("fldOkXd6pQ", "MD-Freight Forwarder"),
            "price_toll": FieldRef("fldsmDhvTs", "MD-Price Toll-Price Level"),
            "price_empty": FieldRef("fldEBKErvy", "MD-Price Empty-Price Level"),
            "price_overweight": FieldRef("fldNNw01Ch", "MD-Price Overweight-Price Level"),
        },
    )

    md_price_cartage = TableDef(
        id="tbl8RJJzlHE4Lt3i",
        name="MD-Price Cartage",
        fields={
            "amount": FieldRef("fldz1Yy4Fg", "Amount"),
            "price_level": FieldRef("fldUH1G681", "Price Level"),
            "cartage_fee_description": FieldRef("fldW8J1qWe", "Cartage Fee Description"),
            "fee_code": FieldRef("fldMvGHZ4m", "Fee Code"),
            "zone_description": FieldRef("fld8mBtoPO", "Zone Description"),
            "ctn_size": FieldRef("fld4qeBNNU", "CTN Size"),
            "deliver_type": FieldRef("fldiwmqPN6", "Deliver Type"),
        },
    )

    md_price_terminal = TableDef(
        id="tbl7MiJUCa1Reo3c",
        name="MD-Price Terminal",
        fields={
            "price_level": FieldRef("fldNYQCXfD", "Price Level"),
            "fee_type": FieldRef("fldc8AeyD8", "Fee Type"),
            "terminal_fee_description": FieldRef("fld32fkhX3", "Terminal Fee Description"),
            "terminal": FieldRef("fldHBa3hgX", "Terminal"),
            "amount": FieldRef("fldrNuEXuH", "Amount"),
        },
    )

    md_price_empty = TableDef(
        id="tbledfARPS0C7736",
        name="MD-Price Empty",
        fields={
            "amount": FieldRef("fldol7d7pq", "Amount"),
            "price_level": FieldRef("fldQoWbeNq", "Price Level"),
            "text3": FieldRef("fldjNnCEbm", "文本 3"),
            "empty_park": FieldRef("fldvSqXbli", "MD-Empty Park"),
            "description": FieldRef("fldYc0KeEA", "Description"),
            "empty_class": FieldRef("fldVkWQVng", "Empty Class"),
        },
    )

    md_price_extra = TableDef(
        id="tblTPoMIzQ1tQ54q",
        name="MD-Price Extra",
        fields={
            "condition": FieldRef("fldHK2MWzu", "Condition"),
            "price_level": FieldRef("fldN8sEDzG", "Price Level"),
            "fee_code": FieldRef("fldRNWzHY9", "Fee Code"),
            "extra_surcharge_description": FieldRef("fldTcFKk3T", "Extra Surcharge Description"),
            "amount": FieldRef("fldvf0lnqE", "Amount"),
            "unit": FieldRef("fldC4uz9H3", "Unit"),
        },
    )

    md_price_overweight = TableDef(
        id="tblxsPlQkKKsd5K3",
        name="MD-Price Overweight",
        fields={
            "overweight_surcharge_description": FieldRef("fldUg0cLdx", "Overweight Surcharge Description"),
            "price_level": FieldRef("fldhsgSsqO", "Price Level"),
            "amount": FieldRef("fldL0ScDIJ", "Amount"),
            "deliver_type": FieldRef("fldayCdZIy", "Deliver Type"),
            "weight_range": FieldRef("fldP7UcDDZ", "Weight Range"),
        },
    )

    md_price_toll = TableDef(
        id="tblCpSWQ8QPQJSgJ",
        name="MD-Price Toll",
        fields={
            "toll_surcharge_description": FieldRef("fldzFM5zd3", "Toll Surcharge Description"),
            "amount": FieldRef("fldH6QRCRb", "Amount"),
            "price_level": FieldRef("fldp5OU1lX", "Price Level"),
        },
    )

    op_cartage = TableDef(
        id="tblKUPmqga4woLk5",
        name="Op-Cartage",
        fields={
            "id": FieldRef("fldH5XYIr7", "ID"),
            "sub_carrier_config": FieldRef("fldMfFJs7p", "Sub Carrier Config"),
            "deliver_config": FieldRef("fldc7tAFc9", "Deliver Config"),
            "booking_reference": FieldRef("fld8VmaJDw", "Booking Reference"),
            "fn_notes": FieldRef("fldbjZU0Kn", "FN Notes"),
            "consingnee_name": FieldRef("fldh6JXNV6", "Consingnee Name"),
            "cartage_advise": FieldRef("fldfFA40gd", "Cartage Advise"),
            "remark": FieldRef("fldcPV88bT", "Remark"),
            "export_booking": FieldRef("fldieHgU2X", "Export Booking"),
            "contact_email": FieldRef("fldUesOVQW", "Contact Email"),
            "import_booking": FieldRef("fldM45Xqfe", "Import Booking"),
            "op_allocator": FieldRef("fldy8i5KDX", "Op-Allocator"),
            "logistics_status": FieldRef("fldNIp07QH", "Logictics Status"),
            "record_status": FieldRef("fld142fIbq", "Record Status"),
            "source_cartage": FieldRef("fldNRApgGD", "Source Cartage"),
            "completed_confirm": FieldRef("fldPTO97lU", "Completed Confirm"),
        },
    )

    op_vessel_schedule = TableDef(
        id="tblSB69pB2YPYUqK",
        name="Op-Vessel Schedule",
        fields={
            "last_free": FieldRef("fldfKyON5q", "Last Free"),
            "voyage": FieldRef("fldrrcw2RN", "Voyage"),
            "etd": FieldRef("fldpNl3G8T", "ETD"),
            "terminal_name": FieldRef("fldhUukDCV", "Terminal Name"),
            "export_cutoff": FieldRef("fldaUqEGP5", "Export Cutoff"),
            "vessel_name": FieldRef("fldF0y8FWM", "Vessel Name"),
            "base_node": FieldRef("fldUDKrZjB", "Base Node"),
            "op_import": FieldRef("fldtUjltb3", "Op-Import"),
            "actual_arrival": FieldRef("fldMdeGuDX", "Actual Arrival"),
            "export_start": FieldRef("fldDtKrKUV", "Export Start"),
            "op_export": FieldRef("fldan0Izqq", "Op-Export"),
            "first_free": FieldRef("fldMokJg6H", "First Free"),
            "eta": FieldRef("fldsCD2Y6D", "ETA"),
            "full_vessel_name": FieldRef("fldadZy1SU", "FULL Vessel Name"),
            "live_port_data": FieldRef("fldxC3ljVW", "Live Port Data"),
        },
    )

    op_import = TableDef(
        id="tblYS3JiR1KiU2hO",
        name="Op-Import",
        fields={
            "container_number": FieldRef("fldfVZBhAB", "Container Number"),
            "gross_weight": FieldRef("fldFyQRSDr", "Gross Weight"),
            "commodity_in": FieldRef("fldY1HSfiZ", "CommodityIn"),
            "container_type": FieldRef("fldA4MiTcq", "Container Type"),
            "container_weight": FieldRef("fldUQEGEGx", "Container Weight"),
            "vessel_in": FieldRef("fld54OXglR", "VesselIn"),
            "terminal_full_name": FieldRef("fldVQJc5Er", "Terminal Full Name"),
            "edo_file": FieldRef("fldWYHpHwX", "EDO File"),
            "storage_start_date": FieldRef("fld0vqVYW7", "StorageStartDate"),
            "op_cartage": FieldRef("fldN5bvBQC", "Op-Cartage"),
            "shipping_line": FieldRef("fld90ybMym", "Shipping Line"),
            "edo_pin": FieldRef("fldSdkHVRs", "EDO PIN"),
            "first_free": FieldRef("fldtiQ55lt", "First Free"),
            "empty_park": FieldRef("fldANf4tNr", "Empty Park"),
            "iso": FieldRef("fldQvi4MXE", "ISO"),
            "detention_days": FieldRef("fld945Ke2j", "Dention Days"),
            "commodity": FieldRef("fld40w6LQV", "Commodity"),
            "import_availability": FieldRef("fldtWj1lfU", "ImportAvailability"),
            "full_vessel_name": FieldRef("fldiyb1MLi", "FULL Vessel Name"),  # link → Op-Vessel Schedule
            "terminal_name": FieldRef("fld6cJPAxN", "Terminal Name"),  # link → MD-Terminal
            "eta": FieldRef("fldvsf9koU", "ETA"),  # datetime
            "in_voyage": FieldRef("fldeOtdPuE", "InVoyage"),
            "last_free": FieldRef("fld5xRtaq8", "Last Free"),
            "on_board_vessel_time": FieldRef("fldpgV4MeC", "ON_BOARD_VESSEL_Time"),
            "on_board_vessel": FieldRef("fldMoSJMeC", "ON_BOARD_VESSEL"),
            "discharge_time": FieldRef("fldafQLMw2", "DISCHARGE_Time"),
            "discharge": FieldRef("fld1RJa0Ji", "DISCHARGE"),
            "estimated_arrival": FieldRef("fldzxIVjfb", "EstimatedArrival"),
            "port_of_discharge": FieldRef("flddSwmxQh", "PortOfDischarge"),
            "gateout_time": FieldRef("fldD3FIVbO", "GATEOUT_Time"),
            "gateout": FieldRef("fldELjpWia", "GATEOUT"),
            "quarantine": FieldRef("fldLWaEpR3", "Quarantine"),
            "clear_status": FieldRef("fld7OEef4K", "Clear Status"),
            "record_status": FieldRef("fldEwvsGtt", "Record Status"),
            "source_edo": FieldRef("fldgijIfl5", "Source EDO"),
            "full_vessel_in": FieldRef("fldxqMZLHT", "Full Vessel In"),
            "add_container": FieldRef("fldFix50cC", "Add Container"),
        },
    )

    op_export = TableDef(
        id="tblKCAzuxD8Jouvt",
        name="Op-Export",
        fields={
            "release_qty": FieldRef("fldqNDp8tU", "Release Qty"),
            "shipping_line": FieldRef("fldsLIDX1o", "Shipping Line"),
            "container_type": FieldRef("fldUqO65I1", "Container Type"),
            "ready_date": FieldRef("fld4z16fdj", "Ready Date"),
            "op_cartage": FieldRef("flds5Z5z2q", "Op-Cartage"),
            "release_status": FieldRef("fldC061ngb", "Release Status"),
            "qty_on_release": FieldRef("fldWFF50QD", "Qty On Release"),
            "expiry_date": FieldRef("fldJh5mh1y", "Expiry Date"),
            "commodity": FieldRef("fldAfxNoKy", "Commodity"),
            "booking_reference": FieldRef("fld1Ltetri", "Booking Reference"),
            "container_number": FieldRef("fldkyvwaIi", "Container Number"),
            "full_vessel_name": FieldRef("fldZnmbuOz", "FULL Vessel Name"),
            "empty_park": FieldRef("fldIyByU7P", "Empty Park"),
        },
    )

    op_trip = TableDef(
        id="tblI7wx6V6LfMDA2",
        name="Op-Trip",
        fields={
            "cartage_info": FieldRef("fld4Ihi00f", "Cartage Info"),
            "action_status": FieldRef("fld5Kf75zo", "Action Status"),
            "prime_mover": FieldRef("fldkb54l3o", "Prime Mover"),
            "date_time": FieldRef("fldhJNK6Bn", "Date & Time"),
            "trailer": FieldRef("fld0FAY1sr", "Trailer"),
            "driver": FieldRef("fld7EBCU7K", "Driver"),
            "logistics_status": FieldRef("fldm1tym1w", "Logictics Status"),
            "trip": FieldRef("fldJFJaQuf", "Trip"),
        },
    )

    dict_table = TableDef(
        id="tblfGiOEkdufx98J",
        name="Dict Table",
        fields={
            "id": FieldRef("fldG7uepTU", "ID"),
            "start_place_type": FieldRef("fldf7JbjoL", "StartPlaceType"),
            "deliver_type": FieldRef("fldjLAq3Ow", "Deliver Type"),
            "state": FieldRef("fldUhr3Fua", "State"),
            "container_type": FieldRef("fldwIH6QXX", "Container Type"),
            "commodity": FieldRef("fldb9xlopW", "Commodity"),
            "action_status": FieldRef("fldfSfYriY", "Action Status"),
        },
    )

    dt_container_type = TableDef(
        id="tblvJAVKWL3OMoNV",
        name="DT-Container Type",
        fields={
            "iso": FieldRef("fld1XVOXEM", "ISO"),
            "container_type": FieldRef("fld8Oq0Be1", "Container Type"),
        },
    )

    dt_commodity = TableDef(
        id="tblKYHYftSjvnKq8",
        name="DT-Commodity",
        fields={
            "commodity": FieldRef("fldtA7uHXc", "Commodity"),
            "commodity_in": FieldRef("fldiJjo4bo", "CommodityIn"),
        },
    )


T = _Tables()
