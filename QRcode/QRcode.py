import qrcode

qr = qrcode.make("https://filafree.vercel.app/")
qr.save("filafree_qr.png")
