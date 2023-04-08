from PIL import Image
import argparse
import logging


def byte_to_fragments(n, bits_per_byte):
    fragments_per_byte = 8 // bits_per_byte  # number of fragments needed to store a byte of data
    divisor = pow(2, bits_per_byte)          # number of values storable in the bits used for encoding
    remaining = n
    res = [0 for _ in range(fragments_per_byte)]
    pos = -1
    while remaining:
        res[pos] = remaining % divisor
        remaining //= divisor
        pos -= 1
    return res


def fragments_to_byte(fragments, bits_per_byte):
    fragments_per_byte = 8 // bits_per_byte  # number of fragments needed to store a byte of data
    divisor = pow(2, bits_per_byte)          # number of values storable in the bits used for encoding
    assert len(fragments) == fragments_per_byte

    res = 0
    for fragment in fragments:
        res = res * divisor + fragment
    return res


# The number of bytes of the message is encoded in a header at the beginning of the image
# This is required to know how many pixels must be read when decoding the message
# This number of bytes is encoded in 4 bytes, so it supports up to 256^4 fragments (over 4 billion)
def get_header_bytes(message_bytes_len):
    assert message_bytes_len < pow(256, 4), 'ERROR - Exceed max supported header size'
    res = []
    remaining = message_bytes_len
    for _ in range(4):
        res = [remaining % 256] + res
        remaining //= 256
    logging.info(f'4 bytes header : {res}')
    return res


# Get the bytes of the header and the message to hide in the image
def get_bytes_to_encode(message):
    message_bytes = bytearray(message, 'utf-8')
    message_bytes_len = len(message_bytes)
    # Add a 4-bytes header containing the number of bytes in the message
    return get_header_bytes(message_bytes_len) + [x for x in message_bytes]


def check_image(img, required_slots):
    # We limit the process to RGB images with 3 color bands
    # The code could obviously be adapted to grayscale with a single band or RGBA with a 4th band
    assert img.mode == 'RGB', 'ERROR - Invalid image mode, only RGB is supported'

    # We need the image to be big enough to contain the entire message
    width, height = img.size
    slots = width * height * 3    # 3 color bands R / G / B
    assert slots >= required_slots, 'ERROR - Message too long for this image'
    logging.info(f'Usage of available slots in the image : {required_slots}/{slots} ({100 * required_slots // slots}%)')


def hide_bytes_in_image(img, bytes_fragments, bits_per_byte):
    divisor = pow(2, bits_per_byte)          # number of values storable in the bits used for encoding
    pixel_x, pixel_y, pixel_band = (0, 0, 0)    # band 0 = R, 1 = G, 2 = B

    for fragment in bytes_fragments:
        # hide this fragment in the next available slot of the image
        coord = pixel_x, pixel_y
        curr_rgb = img.getpixel(coord)
        new_rgb = [x for x in curr_rgb]
        new_rgb[pixel_band] = curr_rgb[pixel_band] - (curr_rgb[pixel_band] % divisor) + fragment
        img.putpixel(coord, tuple(new_rgb))

        # move to the next band of the pixel, or to the next pixel
        pixel_band += 1
        if pixel_band == 3:
            pixel_band = 0
            pixel_x += 1
            if pixel_x == img.width:
                pixel_x = 0
                pixel_y += 1
                assert pixel_y <= img.height, 'ERROR - Message too long for this image'


def extract_fragments(img, fragments_count, bits_per_byte):
    divisor = pow(2, bits_per_byte)          # number of values storable in the bits used for encoding

    pixel_x = pixel_y = pixel_band = 0
    extracted = 0
    res = []
    while True:
        coord = pixel_x, pixel_y
        res.append(img.getpixel(coord)[pixel_band] % divisor)
        extracted += 1

        # returns if it was the last fragment to retrieve
        if extracted == fragments_count:
            return res

        # move to the next slot
        pixel_band += 1
        if pixel_band == 3:
            pixel_band = 0
            pixel_x += 1
            if pixel_x == img.width:
                pixel_x = 0
                pixel_y += 1
                assert pixel_y <= img.height, 'ERROR - No more fragments to extract'


def extract_bytes_from_image(img, bits_per_byte):
    fragments_per_byte = 8 // bits_per_byte  # number of fragments needed to store a byte of data

    # get the fragments encoding the header
    header_fragments_count = 4 * fragments_per_byte
    header_fragments = extract_fragments(img, header_fragments_count, bits_per_byte)
    logging.info(f'Header fragments : {header_fragments}')

    # get the bytes and the value of the header
    header_bytes = []
    for i in range(4):
        byte_fragments = header_fragments[i * fragments_per_byte:(i + 1) * fragments_per_byte]
        header_bytes.append(fragments_to_byte(byte_fragments, bits_per_byte))
    logging.info(f'Header bytes : {header_bytes}')
    message_bytes_count = 256 * (256 * (256 * header_bytes[0] + header_bytes[1]) + header_bytes[2]) + header_bytes[3]
    logging.info(f'Header value : {message_bytes_count}')

    # get all fragments of the encoded message
    message_fragments_count = message_bytes_count * fragments_per_byte
    total_fragments = header_fragments_count + message_fragments_count
    message_fragments = extract_fragments(img, total_fragments, bits_per_byte)[header_fragments_count:]
    logging.info(f'Extracted {message_fragments_count} message fragments.')

    # convert message fragments back into bytes
    message_bytes = []
    for i in range(message_fragments_count // fragments_per_byte):
        fragments = message_fragments[i * fragments_per_byte:(i + 1) * fragments_per_byte]
        message_bytes.append(fragments_to_byte(fragments, bits_per_byte))
    logging.info(f'Size of message bytes : {message_bytes_count}')
    return message_bytes


def encode_message(message_url, bits_per_byte, image_url, output_url):

    with open(message_url, 'r', encoding='utf-8') as f:
        message = f.read()
    logging.info(f'Size of the message string : {len(message)}')

    # Get the bytes representation of the message to encode
    message_bytes = get_bytes_to_encode(message)
    logging.info(f'Size of the message bytes (including 4-bytes header) : {len(message_bytes)}')

    # Split each byte of the message into fragments, that will each be hidden inside one slot of the image
    message_fragments_split = [byte_to_fragments(x, bits_per_byte) for x in message_bytes]
    message_fragments = [x for fragment in message_fragments_split for x in fragment]
    logging.info(f'Size of the bytes fragments : {len(message_fragments)}')

    # get the image to hide the message into, and ensure it is big enough to hide the entire message
    with Image.open(image_url) as img:
        img.load()
    logging.info(f'Input image {image_url} loaded.')
    check_image(img, len(message_fragments))

    # hide the message inside the image and save the new image containing the hidden message
    hide_bytes_in_image(img, message_fragments, bits_per_byte)
    img.save(output_url)
    logging.info(f'Encoded message in image : {output_url}')


def decode_message(bits_per_byte, image_url, output_url):

    with Image.open(image_url) as img:
        img.load()
    logging.info(f'Loaded image {image_url}')

    # extract message bytes from the image
    message_bytes = extract_bytes_from_image(img, bits_per_byte)

    # convert bytes to UTF-8
    decoded_message = bytearray(message_bytes).decode('utf-8')
    logging.info(f'Size of the decoded message : {len(decoded_message)}')

    with open(output_url, 'w') as f:
        f.write(decoded_message)
    logging.info(f'Saved decoded message to {output_url}')


def parse_arguments():
    # define parser
    arg_parser = argparse.ArgumentParser(prog='ImageStenography')
    arg_parser.add_argument('-a', '--action', type=str, choices=['encode', 'decode'],
                            help='encode or decode')
    arg_parser.add_argument('-m', '--message', type=str,
                            help='the input message to encode (required when encoding)')
    arg_parser.add_argument('-i', '--image', type=str, required=True,
                            help='the input image')
    arg_parser.add_argument('-o', '--output', type=str, required=True,
                            help='the output image file (for encode) or message file (for decode)')
    # support only 1, 2, 4 or 8 bits of each image byte to use to encode the image
    arg_parser.add_argument('-b', '--bits-per-byte', type=int, default=2, choices=[1, 2, 4, 8],
                            help='number of bits are used for the encoded message inside each image byte')
    # parse process arguments
    args = arg_parser.parse_args()
    # additional checks
    if args.action == 'encode':
        assert args.message, 'The --message parameter is required for action "encode"'
    # return the arguments
    return args


if __name__ == '__main__':
    # setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s - %(message)s')

    # specify the arguments format and extract arguments
    args = parse_arguments()
    bits_per_byte = args.bits_per_byte
    image_url = args.image
    output_url = args.output
    message_url = args.message

    # either encode or decode a message
    if args.action == 'encode':
        encode_message(message_url, bits_per_byte, image_url, output_url)
    else:
        decode_message(bits_per_byte, image_url, output_url)
