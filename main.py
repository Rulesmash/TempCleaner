from tkinter import Tk, Canvas, Button, PhotoImage
from Deleter import deleter
import os

def asset_path(filename):
    Crnt_dir=os.getcwd()
    return os.path.join(Crnt_dir,'assets',filename)

def del_perctemp():
    deleter(1)
def del_temp():
    deleter(2)
def del_prefetch():
    deleter(3)
def del_recent():
    deleter(4)
def delete_all():
    deleter(5)

window = Tk()
window.geometry("472x608")
window.configure(bg = "#FFFFFF")
window.title("Temp Cleaner")
app_icon= PhotoImage(file=asset_path('apicon.png'))
window.iconphoto(True,app_icon)

canvas = Canvas(
    window,
    bg = "#FFFFFF",
    height = 608,
    width = 472,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas.place(x = 0, y = 0)
button_image_1= PhotoImage(
    file=asset_path("button_1.png"))
button_1 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=del_temp,
    relief="raised"
)
button_1.place(
    x=355.0,
    y=181.0,
    width=87.0,
    height=43.0
)

button_2 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=delete_all,
    relief="raised"
)
button_2.place(
    x=355.0,
    y=551.0,
    width=87.0,
    height=43.0
)

button_3 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=del_perctemp,
    relief="raised"
)
button_3.place(
    x=355.0,
    y=110.0,
    width=87.0,
    height=43.0
)

button_4 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=del_recent,
    relief="raised"
)
button_4.place(
    x=355.0,
    y=323.0,
    width=87.0,
    height=43.0
)

button_5 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=del_prefetch,
    relief="raised"
)
button_5.place(
    x=355.0,
    y=252.0,
    width=87.0,
    height=43.0
)

canvas.create_rectangle(
    0.0,
    0.0,
    472.0,
    59.0,
    fill="#68CFEB",
    outline="")

canvas.create_text(
    11.0,
    15.0,
    anchor="nw",
    text="Temp Cleaner",
    fill="#000000",
    font=("K2D Regular", 32 * -1)
)

canvas.create_rectangle(
    -1.0,
    529.0,
    471.9999937629382,
    531.9999999549451,
    fill="#000000",
    outline="")

image_image_1 = PhotoImage(
    file=asset_path("image_1.png"))
image_1 = canvas.create_image(
    441.0,
    31.0,
    image=image_image_1
)

image_image_2 = PhotoImage(
    file=asset_path("image_2.png"))
image_2 = canvas.create_image(
    141.0,
    128.0,
    image=image_image_2
)

image_image_3 = PhotoImage(
    file=asset_path("image_3.png"))
image_3 = canvas.create_image(
    141.0,
    199.0,
    image=image_image_3
)

image_image_4 = PhotoImage(
    file=asset_path("image_4.png"))
image_4 = canvas.create_image(
    141.0,
    270.0,
    image=image_image_4
)

image_image_5 = PhotoImage(
    file=asset_path("image_5.png"))
image_4 = canvas.create_image(
    141.0,
    341.0,
    image=image_image_5
)

image_image_6 = PhotoImage(
    file=asset_path("image_6.png"))
image_5 = canvas.create_image(
    141.0,
    569.0,
    image=image_image_6
)


window.resizable(False, False)
window.mainloop()
