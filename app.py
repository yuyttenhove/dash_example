import dash
import dash_bootstrap_components as dbc
from dash import html, Output, Input, State, dcc

app = dash.Dash(prevent_initial_callbacks=True, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME])

total = dbc.Row(
    [
        dbc.Col(html.H2(f"Totaal: €0.00", id="total"), width=3),
        dbc.Col(dbc.Button("Checkout", id="checkout", size="lg"), width=2)
    ], 
    className="my-4")
checkout_counter = dcc.Store(id="checkout_counter", data=0)



def create_inputs_with_callbacks(info):
    rows = []
    callbacks = []
    order_stores = []
    stock_stores = []

    for item_id, item_info in info.items():

        row = dbc.Row(
            children = [
                dbc.Label(item_info["label"], size="lg", width=3),
                dbc.Col(
                    dbc.Input(value=0, size="lg", id=f"{item_id}_input", debounce=True), 
                    width=2
                ),
                dbc.Col(
                    dbc.ButtonGroup(
                        [
                            dbc.Button(
                                html.I(className="fa-solid fa-minus"), 
                                color="danger", 
                                id=f"{item_id}_decrease"
                            ),
                            dbc.Button(
                                html.I(className="fa-solid fa-plus"), 
                                color="success", 
                                id=f"{item_id}_increase"
                            ),
                        ],
                        size="lg",
                    ),
                    width="auto"
                ),
            ],
            className="my-2"
        )

        rows.append(row)

        order_stores.append(dcc.Store(id=f"{item_id}_order_store", data=dict(id=item_id, number=0)))
        stock_stores.append(
            dcc.Store(id=f"{item_id}_stock_store", data=dict(id=item_id, number=item_info["number_in_stock"]))
        )

        @app.callback(
            Output(component_id=f"{item_id}_input", component_property="value"),
            Output(component_id=f"{item_id}_order_store", component_property="data"),
            Input(component_id=f"{item_id}_increase", component_property="n_clicks"),
            Input(component_id=f"{item_id}_decrease", component_property="n_clicks"),
            Input(component_id=f"{item_id}_input", component_property="value"),
            Input(component_id="checkout_counter", component_property="data"),
            State(component_id=f"{item_id}_order_store", component_property="data"),
        )
        def callback(_n_clicks_inc, _n_clicks_dec, input, checkout_flag, cur_order):
            context = dash.callback_context

            current_number_ordered = cur_order["number"]

            if not context.triggered:
                return current_number_ordered, cur_order

            trigger_id = context.triggered[0]['prop_id'].split('.')[0]

            if trigger_id == "checkout_counter":
                # Reset order
                return 0, dict(id=cur_order["id"], number=0)

            if "_input" in trigger_id:
                try:
                    current_number_ordered = int(input)
                except ValueError:
                    # Do nothing if illegal number is entered
                    pass

            elif "increase" in trigger_id:
                current_number_ordered += 1
            elif "decrease" in trigger_id:
                if current_number_ordered > 0:
                    current_number_ordered -= 1
                else:
                    return current_number_ordered, cur_order
            else:
                return current_number_ordered, cur_order
            
            return current_number_ordered, dict(id=cur_order["id"], number=current_number_ordered)

        callbacks.append(callback)

    return rows, callbacks, html.Div(order_stores, id="order_stores"), html.Div(stock_stores, id="stock_stores")


info = {
    "cola": dict(label="Cola:", price=1.5, number_in_stock=10), 
    "fanta": dict(label="Fanta:", price=1.75, number_in_stock=7)
}
rows, callbacks, order_stores, stock_stores = create_inputs_with_callbacks(info)


# Create one big callback to update the total if one of the order stores is updated
@app.callback(
    Output("total", "children"),
    [Input(store.id, "data") for store in order_stores.children],
)
def update_total(*args):
    total = 0

    for order in args:
        total += info[order["id"]]["price"] * order["number"]

    return f"Totaal: €{total:.2f}"


# Stock overzicht

table_header = [
    html.Thead(html.Tr([html.Th("Item"), html.Th("Aantal")]))
]

table_rows = [html.Tr([html.Td(item_info["label"]), html.Td(item_info["number_in_stock"])]) 
              for item_info in info.values()]
table_body = [html.Tbody(table_rows, id="table_body")]

table = dbc.Table(table_header + table_body, bordered=True, className="my-3")


# Callback to update stock and increment checkout counter if checkout is pressed
@app.callback(
    Output("checkout_counter", "data"),
    Output("stock_stores", "children"),
    Input("checkout", "n_clicks"),
    State("order_stores", "children"), 
    State("stock_stores", "children"), 
)
def checkout_callback(n_clicks, order_stores, stock_stores):

    # update stock stores
    updated_stock_stores = []
    for stock, order in zip(stock_stores, order_stores):
        new_stock_info = dict(id=stock["props"]["data"]["id"], number=stock["props"]["data"]["number"] - order["props"]["data"]["number"])
        updated_stock_stores.append(dcc.Store(id=stock["props"]["id"], data=new_stock_info))

    return n_clicks, updated_stock_stores


# Callback to update stock table
@app.callback(
    Output("table_body", "children"),
    Input("stock_stores", "children"), 
)
def checkout_callback(stock_stores):

    table_rows = []
    for store in stock_stores:
        item_id = store["props"]["data"]["id"]
        item_stock = store["props"]["data"]["number"]
        item_label = info[item_id]["label"]
        table_rows.append(html.Tr([html.Td(item_label), html.Td(item_stock)]))

    return table_rows


app.layout = dbc.Container(
    [
        dbc.Tabs([
            dbc.Tab(
                [
                    html.Div(rows),
                    total,
                ],
                label="Plaats een order"
            ),
            dbc.Tab(
                table,
                label="Overzicht stock"
            ),
        ]),
        html.Div([order_stores, stock_stores, checkout_counter])
    ],
    className="p-5",
)

if __name__ == "__main__":
    app.run_server(debug=False)