import unittest
import os
import steganography_image as stegano


class MyTestCase(unittest.TestCase):

    def test_byte_to_fragments(self):
        # 8 bits per byte used for encoding (fragments between 0 and 255)
        self.assertEqual(stegano.byte_to_fragments(4, 8), [4])
        self.assertEqual(stegano.byte_to_fragments(252, 8), [252])
        # 4 bits per byte used for encoding (fragments between 0 and 15)
        self.assertEqual(stegano.byte_to_fragments(4, 4), [0, 4])
        self.assertEqual(stegano.byte_to_fragments(252, 4), [15, 12])
        # 2 bits per byte used for encoding (fragments between 0 and 3)
        self.assertEqual(stegano.byte_to_fragments(4, 2), [0, 0, 1, 0])
        self.assertEqual(stegano.byte_to_fragments(252, 2), [3, 3, 3, 0])
        # 1 bit per byte used for encoding (fragments between 0 and 1)
        self.assertEqual(stegano.byte_to_fragments(4, 1), [0, 0, 0, 0, 0, 1, 0, 0])
        self.assertEqual(stegano.byte_to_fragments(252, 1), [1, 1, 1, 1, 1, 1, 0, 0])

    def test_fragments_to_byte(self):
        # 8 bits per byte used for encoding (fragments between 0 and 255)
        self.assertEqual(stegano.fragments_to_byte([4], 8), 4)
        self.assertEqual(stegano.fragments_to_byte([252], 8), 252)
        # 4 bits per byte used for encoding (fragments between 0 and 15)
        self.assertEqual(stegano.fragments_to_byte([0, 4], 4), 4)
        self.assertEqual(stegano.fragments_to_byte([15, 12], 4), 252)
        # 2 bits per byte used for encoding (fragments between 0 and 3)
        self.assertEqual(stegano.fragments_to_byte([0, 0, 1, 0], 2), 4)
        self.assertEqual(stegano.fragments_to_byte([3, 3, 3, 0], 2), 252)
        # 1 bit per byte used for encoding (fragments between 0 and 1)
        self.assertEqual(stegano.fragments_to_byte([0, 0, 0, 0, 0, 1, 0, 0], 1), 4)
        self.assertEqual(stegano.fragments_to_byte([1, 1, 1, 1, 1, 1, 0, 0], 1), 252)

    def test_get_header_bytes(self):
        # the header contains the size encoded on 4 bytes
        self.assertEqual(stegano.get_header_bytes(4), [0, 0, 0, 4])
        self.assertEqual(stegano.get_header_bytes(256 * 255), [0, 0, 255, 0])
        self.assertEqual(stegano.get_header_bytes(256 * 256 * 256 * 3 + 2), [3, 0, 0, 2])

    def test_encode_decode(self):
        message_url = 'test_data/grimm_fairy_tales.txt'
        image_url = 'test_data/himeji.png'
        encoded_image_url = 'test_data/himeji_encoded.png'
        decoded_message_url = 'test_data/decoded_message.txt'
        bits_per_byte = 4
        # encode the message in an image
        stegano.encode_message(message_url, bits_per_byte, image_url, encoded_image_url)
        # decode the message from that image
        stegano.decode_message(bits_per_byte, encoded_image_url, decoded_message_url)
        # ensure the initial original message and the decoded message are equal
        with open(message_url, 'r') as f1:
            initial_message = f1.read()
        with open(decoded_message_url, 'r') as f2:
            decoded_message = f2.read()
        self.assertEqual(initial_message, decoded_message)
        # cleanup generated files
        os.remove(encoded_image_url)
        os.remove(decoded_message_url)


if __name__ == '__main__':
    unittest.main()
