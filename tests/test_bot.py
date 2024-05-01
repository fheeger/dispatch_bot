import unittest
from unittest import IsolatedAsyncioTestCase

class StartGame(IsolatedAsyncioTestCase):
    async def setUp(self):
        await setup_channels()

    async def test_start_game(self):
        result = await functionality()
        self.assertEqual(expected, result)


if __name__ == '__main__':

    unittest.main()

