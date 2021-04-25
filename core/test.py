import unittest
import random

from core.engine import *


class TestIndexation(unittest.TestCase):
    def test01_serialization(self):
        token_file_name = './core/tokens.txt'
        dictionary_file_name = './core/dictionary.bin'
        inverse_index_file_name = './core/inverse_index.bin'
        straight_index_file_name = './core/straight_index.bin'
        coordinate_file_name = './core/coordinate_index.bin'
        jump_table_file_name = './core/jump_table.bin'
        inverse_index_title_file_name = './core/inverse_title_index.bin'
        coordinate_index_title_file_name = './core/coordinate_title_index.bin'
        dictionary, straight_index, dictionary_pages, \
        coordinates, coordinates_title = indexation(token_file_name, dictionary_file_name,
                                                    inverse_index_file_name, straight_index_file_name,
                                                    coordinate_file_name, jump_table_file_name,
                                                    inverse_index_title_file_name,
                                                    coordinate_index_title_file_name, test=True)
        dictionary_read = read_dictionary(dictionary_file_name)
        straight_index_read = read_straight_index(straight_index_file_name)
        self.assertDictEqual(dictionary, dictionary_read)
        self.assertDictEqual(straight_index, straight_index_read)
        for term in dictionary_pages:
            number_ids, offset, _, offset_title = dictionary_read[hash_used(term)]
            page_ids = read_page_ids(inverse_index_file_name, offset)
            page_ids_title = read_page_ids(inverse_index_title_file_name, offset_title)
            self.assertListEqual([x[0] for x in page_ids], dictionary_pages[term])
            for page_id, offset in page_ids:
                coord = read_coordinates(coordinate_file_name, offset)
                self.assertListEqual(coord, coordinates[hash_used(term)][page_id])
            for page_id, offset in page_ids_title:
                coord = read_coordinates(coordinate_index_title_file_name, offset)
                self.assertListEqual(coord, coordinates_title[hash_used(term)][page_id])

    def test02_empirical_index_current(self):
        token_file_name = './core/tokens.txt'
        dictionary_file_name = './core/dictionary.bin'
        inverse_index_file_name = './core/inverse_index.bin'
        straight_index_file_name = './core/straight_index.bin'
        coordinate_file_name = './core/coordinate_index.bin'
        jump_table_file_name = './core/jump_table.bin'
        inverse_index_title_file_name = './core/inverse_title_index.bin'
        coordinate_index_title_file_name = './core/coordinate_title_index.bin'

        dictionary = read_dictionary(dictionary_file_name)

        page_to_terms = dict()
        page_to_terms[84966] = ['quake', 'scourge', 'of', 'armagon', 'первый',
                                'набор', 'дополнительных', 'миссий', 'к', 'игре']
        page_to_terms[88956] = ['dungeon', 'keeper', '2', 'хранитель', 'подземелья', 'или', 'сокращённо', 'dk2',
                                'продолжение', 'игры', 'выпущенной', 'компанией', 'bullfrog', 'productions', 'и',
                                'изданная', 'компанией', 'electronic', 'arts']
        page_to_terms[84591] = ['wolfenstein', '3d', 'компьютерная', 'игра', 'в', 'жанре', 'шутера', 'от', 'первого',
                                'лица', 'разработанная', 'компанией', 'id', 'software', 'и', 'изданная', 'apogee',
                                'software']

        for page_id in page_to_terms.keys():
            for term in page_to_terms[page_id]:
                term = term.lower()
                term = remove_rus_ending(term)
                number_ids, offset, _, offset_title = dictionary[hash_used(term)]
                page_ids = read_page_ids(inverse_index_file_name, offset)
                page_ids_title = read_page_ids(coordinate_index_title_file_name, offset_title)
                self.assertTrue(page_id in [x[0] for x in page_ids] or page_id in [x[0] for x in page_ids_title])

    def test03_jump_tables_current(self):
        token_file_name = './core/tokens.txt'
        dictionary_file_name = './core/dictionary.bin'
        inverse_index_file_name = './core/inverse_index.bin'
        straight_index_file_name = './core/straight_index.bin'
        coordinate_file_name = './core/coordinate_index.bin'
        jump_table_file_name = './core/jump_table.bin'
        inverse_index_title_file_name = './core/inverse_title_index.bin'
        coordinate_index_title_file_name = './core/coordinate_title_index.bin'
        dictionary = read_dictionary(dictionary_file_name)

        for key in dictionary.keys():
            number_ids, offset, jump_table_offset, _ = dictionary[key]
            if jump_table_offset > -1:
                jump_table = read_jump_table(jump_table_file_name, jump_table_offset)
                page_ids_by_blocks = read_block_page_ids(jump_table, -1, inverse_index_file_name, offset)

                for block_id in range(len(jump_table)):
                    page_ids_by_blocks.extend(read_block_page_ids(jump_table, block_id, inverse_index_file_name, offset))

                self.assertListEqual(page_ids_by_blocks, [x for x, y in read_page_ids(inverse_index_file_name, offset)])

    def test04_title_index_current(self):
        token_file_name = './core/tokens.txt'
        dictionary_file_name = './core/dictionary.bin'
        inverse_index_file_name = './core/inverse_index.bin'
        straight_index_file_name = './core/straight_index.bin'
        coordinate_file_name = './core/coordinate_index.bin'
        jump_table_file_name = './core/jump_table.bin'
        inverse_index_title_file_name = './core/inverse_title_index.bin'
        coordinate_index_title_file_name = './core/coordinate_title_index.bin'

        dictionary = read_dictionary(dictionary_file_name)
        straight_index = read_straight_index(straight_index_file_name)

        for page_id in straight_index.keys():
            for term in straight_index[page_id][1].split():
                term = term.lower()
                term = remove_rus_ending(term)
                _, _, _, offset = dictionary[hash_used(term)]
                page_ids = read_page_ids(inverse_index_title_file_name, offset)
                self.assertTrue(page_id in [x[0] for x in page_ids])


class TestSearch(unittest.TestCase):
    def test01_RPN_positive(self):
        infix = ['qwe && ewq\n', '(qwe &&ewq) r ty', '!q&&(we||r)&&fgh&&(ert&&(zxc||!uio))\n',
                 ' ! q ( we ||      r   )  fgh (   ert  && ( zxc         ||  !    uio  )   )   \n',
                 '[!q&&(we||r)&&fgh&&(ert&&{zxc||!uio})]', '(qwe || !ew) && (ewq || (asd && !uy))',
                 '! (qwe&&rty||df j)     ', 'qwe df || qwe rt y', '"qwe ewq: asd?" rty uuu',
                 'rty "qwe ewq: asd?"&&uuu', '"qwe ewq: asd?"', '   "qwe ewq: asd?"/   10|| dfg',
                 '  [ {  "qwe ewq: asd?"/   10}|| (dfg || fgh)]', '"qwe ewq: asd?"/2', 'xcv !"qwe ewq: asd?"/2',
                 '"Дополнение продолжает оригинальный Quake" "через месяца месяца" / 3',
                 '"Дополнение продолжает оригинальный Quake"/ 56 "через месяца месяца" / 3'
                 ]
        rpn = [['qwe', 'ewq', '&&'], ['qwe', 'ewq', '&&', 'r', '&&', 'ty', '&&'],
               ['q', '!', 'we', 'r', '||', '&&', 'fgh', '&&', 'ert', 'zxc', 'uio', '!', '||', '&&', '&&'],
               ['q', '!', 'we', 'r', '||', '&&', 'fgh', '&&', 'ert', 'zxc', 'uio', '!', '||', '&&', '&&'],
               ['q', '!', 'we', 'r', '||', '&&', 'fgh', '&&', 'ert', 'zxc', 'uio', '!', '||', '&&', '&&'],
               ['qwe', 'ew', '!', '||', 'ewq', 'asd', 'uy', '!', '&&', '||', '&&'],
               ['qwe', 'rty', '&&', 'df', 'j', '&&', '||', '!'],
               ['qwe', 'df', '&&', 'qwe', 'rt', '&&', 'y', '&&', '||'],
               [[['qwe', 'ewq', 'asd'], 2], 'rty', '&&', 'uuu', '&&'],
               ['rty', [['qwe', 'ewq', 'asd'], 2], '&&', 'uuu', '&&'],
               [[['qwe', 'ewq', 'asd'], 2]], [[['qwe', 'ewq', 'asd'], 10], 'dfg', '||'],
               [[['qwe', 'ewq', 'asd'], 10], 'dfg', 'fgh', '||', '||'],
               [[['qwe', 'ewq', 'asd'], 2]],
               ['xcv', [['qwe', 'ewq', 'asd'], 2], '!', '&&'],
               [[['дополнение', 'продолжает', 'оригинальный', 'quake'], 3], [['через', 'месяца', 'месяца'], 3], '&&'],
               [[['дополнение', 'продолжает', 'оригинальный', 'quake'], 56], [['через', 'месяца', 'месяца'], 3], '&&']
               ]

        for i in range(len(infix)):
            test = get_RPN_by_request(infix[i])
            self.assertTrue(test is not None, infix[i])
            self.assertTrue(len(test) == len(rpn[i]), infix[i])
            for j in range(len(rpn[i])):
                self.assertEqual(rpn[i][j], test[j][1], infix[i])

    def test02_RPN_negative(self):
        infix = ['qwe & ewq', '(qwe &&ewq r ty', '!q&&(we||r)||&&fgh&&(ert&&(zxc||!uio))',
                 ' ! q ( we ||      r   )  fgh (   ert  && ( zxc         ||  !    uio  )   )   &&',
                 '[!q&&(we||r)&&fgh&&(ert&&[zxc||!uio})]', '(qwe || !ew) && (ewq || (asd && !uy)',
                 '! (qwe&&rty||df j)    ! ', '&& qwe ||ewq', '"qwe ewq: asd?/2', 'qwe ewq: asd?"/2',
                 '"qwe ewq: asd?"/', '"qwe ewq: asd?"/ (qwe || asd)', '"qwe ewq: asd?"/01',
                 '"qwe ewq: asd?"2', '"qwe ewq: asd?"/2asd', '"qwe ewq: asd?"//2', '!"qwe ewq: asd?""/2&&qwe',
                 '!""qwe ewq: asd?"/2&&qwe', '""', 'qwe "asd d" fgh "rty ', '  "qwe rty""fgh jh" /  3',
                 ' "qwe rty uio"/1  ', ' "@ 123 321 11 11" / 2 rty', ' "ert ty" /5tyu', ' "ert ty" /   5tyu'
                 ]

        for i in range(len(infix)):
            test = get_RPN_by_request(infix[i])
            self.assertTrue(test is None, infix[i])
            i += 1

    def test03_search(self):
        dictionary_file_name = './core/dictionary.bin'
        inverse_index_file_name = './core/inverse_index.bin'
        all_page_ids_file_name = './core/all_page_ids.bin'
        coordinate_index_file_name = './core/coordinate_index.bin'
        jump_table_file_name = './core/jump_table.bin'
        inverse_index_title_file_name = './core/inverse_title_index.bin'
        coordinate_index_title_file_name = './core/coordinate_title_index.bin'

        requests = ['Quake: Scourge of Armagon', 'Действие игры разворачивается в городе Эшфилд',
                    'doom 1993', 'python (PyCharm || Visual Studio Code || Emacs) ide',
                    'resident evil !wii',
                    'final fantasy (2015 || 2016 || 2017 || 2018 || 2019)',
                    'компилятор c++ windows (Linux ||unix)', 'идеал аскетизма философ',
                    'работа Сади Карно !(президент Франции)', # 43330
                    'принцип шести степеней свободы шутер !(Shattered Horizon)',
                    '"Дополнение продолжает оригинальный Quake"', '"через месяца месяца" / 3',
                    '"Гремлин — внешне напоминает Рогача"',
                    '"Гремлин — внешне напоминает Рогача Основная способность" / 12',
                    '"Дополнение продолжает оригинальный Quake" "через месяца месяца" / 3',
                    '"Дополнение продолжает оригинальный Quake" / 5 || "через месяца месяца" / 3',
                    '"Движок игры был обновлён" "Главный герой возвращается на базу зомбинированных солдат" / 15 "через месяца месяца" / 3'
                    ]
        positive_ids = [[84966], [509283], [84968], [4227719], [3154423],
                        [2384697], [234594], [2995], [], [819887], [84966], [84966], [84966], [84966], [84966],
                        [84966], [84966]
                        ]
        negative_ids = [[52826], [], [], [6246771, 17710], [1011645, 715315], [2228067], [], [],
                        [69114], [1454965], [], [], [], [], [], [], []
                        ]

        dictionary = read_dictionary(dictionary_file_name)
        all_page_ids = read_all_page_ids(all_page_ids_file_name)
        for i in range(len(requests)):
            result, result_title = get_page_ids_by_request(requests[i], dictionary, inverse_index_file_name, all_page_ids,
                                                           coordinate_index_file_name, jump_table_file_name,
                                                           inverse_index_title_file_name, coordinate_index_title_file_name)
            self.assertIsNotNone(result)
            for pos_id in positive_ids[i]:
                self.assertIn(pos_id, result)
            for neg_id in negative_ids[i]:
                self.assertNotIn(neg_id, result)

    def test04_title_search(self):
        dictionary_file_name = './core/dictionary.bin'
        inverse_index_file_name = './core/inverse_index.bin'
        all_page_ids_file_name = './core/all_page_ids.bin'
        coordinate_index_file_name = './core/coordinate_index.bin'
        jump_table_file_name = './core/jump_table.bin'
        inverse_index_title_file_name = './core/inverse_title_index.bin'
        coordinate_index_title_file_name = './core/coordinate_title_index.bin'

        requests = ['Quake: Scourge of Armagon', 'Dungeon Keeper 2', 'Wolfenstein', 'master orion',
                    'Warlords etheria', 'blackthorne', 'Фуллье'
                    ]
        positive_ids = [[84966], [88956], [84591], [150269], [184586], [231098], [1064815]]
        negative_ids = [[52826], [], [], [], [], [], []]

        dictionary = read_dictionary(dictionary_file_name)
        all_page_ids = read_all_page_ids(all_page_ids_file_name)
        for i in range(len(requests)):
            _, result = get_page_ids_by_request(requests[i], dictionary, inverse_index_file_name, all_page_ids,
                                                coordinate_index_file_name, jump_table_file_name,
                                                inverse_index_title_file_name, coordinate_index_title_file_name)
            self.assertIsNotNone(result)
            for pos_id in positive_ids[i]:
                self.assertIn(pos_id, result)
            for neg_id in negative_ids[i]:
                self.assertNotIn(neg_id, result)


class Simple9Test(unittest.TestCase):
    def test01_encode_decode_equal_data(self):
        data = []
        length_data = 1000000
        max_number = 100

        for _ in range(length_data):
            data.append(random.randint(1, max_number))

        self.assertListEqual(simple9_decode(simple9_encode(data)), data)




