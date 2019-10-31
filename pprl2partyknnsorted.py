import os
import time
import bisect
from itertools import tee

from pprlindex import PPRLIndex
from config import SORTED_FIRST_VAL


class PPRLIndex2PartyKAnonymousSortedNeighbour(PPRLIndex):
    """Class that implements a sorted neighbourhood based 2-party PPRL indexing
     technique.

     Blocks are generated by sorting random reference values, and inserting the
     values from the databases into an inverted index where reference values
     are the keys. Blocks are then formed such that each contains at least k
     records. Database owners exchange the reference values at least one from
     each cluster which are sorted over which a slab of width w is moved to
     find the clusters of Alice and Bob to be merged to generate candidate
     record pairs.
  """

    # --------------------------------------------------------------------------

    def __init__(self, k, w, sim_measure, min_sim_threshold, overlap, sim_or_size):
        """Initialise the class and set the required parameters.

       Arguments:
       - k                  The minimum block size (in number of records that
                            need to be in a block).
       - w                  The size of the sliding window in SNN approach.
       - sim_measure        A function which takes two strings as input and
                            returns a similarity value between 0 and 1.
       - min_sim_threshold  A similarity threshold between 0 and 1 which is
                            used to decide if a value is to be added to an
                            existing cluster (if a similarity value is equal
                            to or larger than this minimum threshold, or if a
                            new cluster is to be generated (if the similarity
                            is below this threshold).
       - overlap            An integer value that is used to generate
                            overlapping blocks when generating candidate
                            record pairs.
       - sim_or_size        The merging of blocks is either determined by the
                            minimum similarity between adjacent reference
                            values, or by merging blocks until they each
                            contain k record identifiers.
    """

        self.k = k
        self.w = w
        self.sim_measure = sim_measure
        self.min_sim_threshold = min_sim_threshold

        assert sim_or_size in ['SIM', 'SIZE']
        self.sim_or_size = sim_or_size

        self.ref_val_list_alice = None  # List of selected reference values
        self.ref_val_list_bob = None

        self.ref_ind_dict_alice = None  # Reference values with integer values as keys
        # (with reference values sorted)
        self.ref_ind_dict_bob = None

        self.alice_rep_vals = []
        self.bob_rep_vals = []

        self.alice_rep_index = {}
        self.bob_rep_index = {}

    # --------------------------------------------------------------------------

    def __sort_ref_values_alice__(self):
        """Sort the reference values and assign an integer value (starting from 0)
       to each according to this sorting.
    """

        assert self.ref_val_list_alice != None

        sort_ref_val_list_alice = sorted(self.ref_val_list_alice)

        ref_ind_dict_alice = {}

        ref_ind_dict_alice[0] = SORTED_FIRST_VAL  # Smallest possible value

        ind = 1
        for ref_val in sort_ref_val_list_alice:
            ref_ind_dict_alice[ind] = ref_val
            ind += 1

        self.ref_ind_dict_alice = ref_ind_dict_alice
        self.sort_ref_val_list_alice = sort_ref_val_list_alice

    # --------------------------------------------------------------------------

    def __sort_ref_values_bob__(self):
        """Sort the reference values and assign an integer value (starting from 0)
       to each according to this sorting.
    """

        assert self.ref_val_list_bob != None

        sort_ref_val_list_bob = sorted(self.ref_val_list_bob)

        ref_ind_dict_bob = {}

        ref_ind_dict_bob[0] = SORTED_FIRST_VAL  # Smallest possible value

        ind = 1
        for ref_val in sort_ref_val_list_bob:
            ref_ind_dict_bob[ind] = ref_val
            ind += 1

        self.ref_ind_dict_bob = ref_ind_dict_bob
        self.sort_ref_val_list_bob = sort_ref_val_list_bob

    # --------------------------------------------------------------------------

    def __sort_appropriate_ref_values_alice__(self):
        """Sort the reference values and assign an integer value (starting from 0)
       to each according to this sorting.
    """

        assert self.ref_val_list_alice != None

        random.seed(10)

        sort_ref_val_list_alice = sorted(self.ref_val_list_alice)

        final_ref_val_list_alice = []

        for i in range(len(sort_ref_val_list_alice) - 1):
            this_ref_val = sort_ref_val_list_alice[i]
            if len(final_ref_val_list_alice) == 0:
                final_ref_val_list_alice.append(this_ref_val)
            else:
                prev_ref_val = final_ref_val_list_alice[-1]
                min_len = min(len(this_ref_val), len(prev_ref_val)) / 4
                if (self.sim_measure(this_ref_val[:min_len], prev_ref_val[:min_len]) < 0.6):
                    ##if (stringcmp.winkler(this_ref_val,prev_ref_val) < 0.8):
                    final_ref_val_list_alice.append(this_ref_val)
                else:
                    if len(this_ref_val) > len(prev_ref_val):
                        final_ref_val_list_alice.remove(prev_ref_val)
                        final_ref_val_list_alice.append(this_ref_val)

        selected_ref_val_list_alice = []
        if len(final_ref_val_list_alice) > (ref_vals / 1):
            selected_ref_val_list_alice = random.sample(final_ref_val_list_alice, ref_vals / 1)
        else:
            selected_ref_val_list_alice = final_ref_val_list_alice

        print(len(sort_ref_val_list_alice), len(final_ref_val_list_alice), len(selected_ref_val_list_alice))

        ref_ind_dict_alice = {}

        ref_ind_dict_alice[0] = SORTED_FIRST_VAL  # Smallest possible value

        ind = 1
        for ref_val in selected_ref_val_list_alice:
            ref_ind_dict_alice[ind] = ref_val
            ind += 1

        self.ref_ind_dict_alice = ref_ind_dict_alice
        self.sort_ref_val_list_alice = selected_ref_val_list_alice

    # --------------------------------------------------------------------------

    def __sort_appropriate_ref_values_bob__(self):
        """Sort the reference values and assign an integer value (starting from 0)
       to each according to this sorting.
    """

        assert self.ref_val_list_bob != None

        random.seed(18)  # 18

        sort_ref_val_list_bob = sorted(self.ref_val_list_bob)

        final_ref_val_list_bob = []

        for i in range(len(sort_ref_val_list_bob) - 1):
            this_ref_val = sort_ref_val_list_bob[i]
            if len(final_ref_val_list_bob) == 0:
                final_ref_val_list_bob.append(this_ref_val)
            else:
                prev_ref_val = final_ref_val_list_bob[-1]
                min_len = min(len(this_ref_val), len(prev_ref_val)) / 4
                if (self.sim_measure(this_ref_val[:min_len], prev_ref_val[:min_len]) < 0.6):
                    ##if (stringcmp.winkler(this_ref_val,prev_ref_val) < 0.8):
                    final_ref_val_list_bob.append(this_ref_val)
                else:
                    if len(this_ref_val) > len(prev_ref_val):
                        final_ref_val_list_bob.remove(prev_ref_val)
                        final_ref_val_list_bob.append(this_ref_val)

        selected_ref_val_list_bob = []
        if len(final_ref_val_list_bob) > (ref_vals / 1):
            selected_ref_val_list_bob = random.sample(final_ref_val_list_bob, ref_vals / 1)
        else:
            selected_ref_val_list_bob = final_ref_val_list_bob

        print(len(sort_ref_val_list_bob), len(final_ref_val_list_bob), len(selected_ref_val_list_bob))

        ref_ind_dict_bob = {}

        ref_ind_dict_bob[0] = SORTED_FIRST_VAL  # Smallest possible value

        ind = 1
        for ref_val in selected_ref_val_list_bob:
            ref_ind_dict_bob[ind] = ref_val
            ind += 1

        self.ref_ind_dict_bob = ref_ind_dict_bob
        self.sort_ref_val_list_bob = selected_ref_val_list_bob

    # --------------------------------------------------------------------------

    def __window__(self, iterable, size):
        """Sliding window approach.
    """

        iters = tee(iterable, size)

        for i in range(1, size):
            for each in iters[i:]:
                next(each, None)
        return zip(*iters)

    # --------------------------------------------------------------------------

    def __generate_sorted_index__(self, rec_dict, attr_select_list,
                                  sort_ref_val_list, ref_ind_dict):
        """Generate the blocks for the given record dictionary. Each record (its
       record identifier) is inserted into one block according to the sorting
       key values.
    """

        ## Two different max block size criteria:
        # a) min similarity between reference values
        # b) max number of records in a block to be merged

        assert rec_dict != None
        assert ref_ind_dict != None

        k = self.k

        sim_measure = self.sim_measure
        min_sim_threshold = self.min_sim_threshold

        ref_val_dict = {}  # Reference values and corresponding attribute values
        ref_val_dict[SORTED_FIRST_VAL] = []  # Empty list of attribute for this block

        for ref_val in sort_ref_val_list:
            ref_val_dict[ref_val] = []  # Initialize each block with empty list

        block_dict = {}  # Resulting blocks generated
        blk_keys = []  # Resulting block keys

        num_rec_done = 0

        # Insert the records into the sorted reference dictionary
        #
        for (rec_id, rec_list) in rec_dict.items():
            num_rec_done += 1
            if (num_rec_done % 10000 == 0):
                print(num_rec_done, len(rec_dict))

            # Generate the SKV for this record
            #
            sk_val = ''
            for col_num in attr_select_list:
                sk_val += rec_list[col_num]

            # Find the position of this SKV in the sorted list of ref vals and
            # insert it into the corresponding list of record identifiers in the
            # reference dictionary
            #
            pos = bisect.bisect(sort_ref_val_list, sk_val)
            ref_val = ref_ind_dict[pos]
            skvs_list = ref_val_dict[ref_val]
            # skvs_list.append((sk_val,rec_id))  # Store value and record identifier
            skvs_list.append(rec_id)
            ref_val_dict[ref_val] = skvs_list

        len_sort_ref_list = len(sort_ref_val_list)

        # a) max block criteria - min similarity between ref values
        if self.sim_or_size == 'SIM':
            # Merge blocks if they contain less than k elements
            #
            i = 0
            while i < len_sort_ref_list:
                num_elements = 0
                j = 0
                this_blk_elements_list = []

                sim_val = 0.0
                # The minimum number of elements in a block must be k, while the maximum
                # num of elements depends on the similarity between the ref values
                #
                while (((num_elements <= k) and (i + j < len_sort_ref_list)) or \
                       ((sim_val >= min_sim_threshold) and (i + j < len_sort_ref_list))):
                    this_ref_val = ref_ind_dict[i + j]
                    this_element_list = ref_val_dict[this_ref_val]
                    num_elements += len(this_element_list)
                    this_blk_elements_list += this_element_list

                    # Similarity of the next (if not the last) ref value with this ref value
                    #
                    if ((i + j + 1) != len_sort_ref_list):
                        next_ref_val = ref_ind_dict[i + j + 1]
                        sim_val = sim_measure(this_ref_val, next_ref_val)

                    j += 1

                # If a block contains less than k elements (probably the last block)
                # merge it with the previous block
                #
                if (len(this_blk_elements_list) < k):
                    prev_blk_str = '_' + str(i - 1) + '_'
                    prev_blk_id = next(k for (k, v) in block_dict.items() if \
                                       prev_blk_str in k)
                    prev_blk_elements_list = block_dict[prev_blk_id]
                    this_blk_elements_list += prev_blk_elements_list
                    block_id = prev_blk_id
                    del block_dict[prev_blk_id]  # Delete this block and add a new
                    # merged block
                    blk_keys.remove(prev_blk_id)
                else:
                    block_id = 'b_'

                # Generate the block identifier of this block consisting of the indices
                # of all the reference values in the block
                #
                for b in range(j):
                    block_id += str(i + b) + '_'

                # Insert the list of record identifiers for this block into final dict
                #
                block_dict[block_id] = this_blk_elements_list
                blk_keys.append(block_id)
                i += j

        # print block_dict.keys()
        return block_dict

    # --------------------------------------------------------------------------

    def __select_rep_ref_vals__(self, block_index, ref_ind_dict):
        """Select at least one representative reference value from each cluster
       to send to the other party. These representative values will be sorted
       and SNN will be applied to find the candidate clusters.

       Argument:
       - block_index       k-anonymous clusters: A dictionary with keys being
                           the block key consisting of the integer numbers of
                           the reference values in that block and values are
                           the SKVs in the block.
       - ref_ind_dict      Reference values with integer values as keys
                           (with reference values sorted)
    """

        keys_list = list(block_index.keys())
        rep_ref_vals = []
        rep_index = {}

        for key in keys_list:
            # Get the ids of reference values in each block
            #
            ref_nums_list = key.split('_')
            # First element will be 'b', and last will be empty, so not used
            #
            ref_nums = [int(i) for i in key.split('_')[1:-1]]

            # rep_refs = [random.choice(ref_nums)]
            # rep_ref_vals += rep_refs # 1 ref val

            # ref_25 = len(ref_nums)*1/4
            # rep_refs = random.sample(ref_nums,ref_25)
            # rep_ref_vals += rep_refs                   # 25% of ref vals

            # ref_75 = len(ref_nums)*3/4
            # rep_refs = random.sample(ref_nums,ref_75)
            # rep_ref_vals += rep_refs                     # 75% of ref vals

            # ref_10 = len(ref_nums)*1/10
            # rep_refs = random.sample(ref_nums,ref_10)
            # rep_ref_vals += rep_refs                  # 10% of ref vals

            # ref_20 = len(ref_nums)*1/5
            # rep_refs = random.sample(ref_nums,ref_20)
            # rep_ref_vals += rep_refs                   # 20% of ref vals

            # ref_30 = len(ref_nums)*3/10
            # rep_refs = random.sample(ref_nums,ref_30)
            # rep_ref_vals += rep_refs                   # 30% of ref vals

            # ref_40 = len(ref_nums)*4/10
            # rep_refs = random.sample(ref_nums,ref_40)
            # rep_ref_vals += rep_refs                   # 40% of ref vals

            # ref_50 = len(ref_nums)*5/10
            # rep_refs = random.sample(ref_nums,ref_50)
            # rep_ref_vals += rep_refs                   # 50% of ref vals

            # ref_60 = len(ref_nums)*6/10
            # rep_refs = random.sample(ref_nums,ref_60)
            # rep_ref_vals += rep_refs                   # 60% of ref vals

            # ref_70 = len(ref_nums)*7/10
            # rep_refs = random.sample(ref_nums,ref_70)
            # rep_ref_vals += rep_refs                   # 70% of ref vals

            # ref_80 = len(ref_nums)*8/10
            # rep_refs = random.sample(ref_nums,ref_80)
            # rep_ref_vals += rep_refs                   # 80% of ref vals

            # ref_90 = len(ref_nums)*9/10
            # rep_refs = random.sample(ref_nums,ref_90)
            # rep_ref_vals += rep_refs                   # 90% of ref vals

            rep_refs = ref_nums
            rep_ref_vals += ref_nums  ## all ref vals

            for ref_num in rep_refs:
                ref_val = ref_ind_dict[ref_num]
                if ref_val not in rep_index:
                    rep_index[ref_val] = key

        return rep_ref_vals, rep_index

    # --------------------------------------------------------------------------

    def build_index_alice(self, attr_select_list):
        """Build the index for Alice assuming the sorted reference values have
       been generated.

       Argument:
       - attr_select_list  A list of column numbers that will be used to
                           extract attribute values from the given records,
                           and concatenate them into one string value which is
                           then used as reference value (and added to the
                           result list if it differs from all other reference
                           values).
    """

        start_time = time.time()

        self.attr_select_list_alice = attr_select_list

        self.__sort_ref_values_alice__()
        # self.__sort_appropriate_ref_values_alice__()

        assert self.rec_dict_alice != None
        # print self.sort_ref_val_list_alice
        self.index_alice = self.__generate_sorted_index__(self.rec_dict_alice,
                                                          attr_select_list, self.sort_ref_val_list_alice,
                                                          self.ref_ind_dict_alice)
        print('Index for Alice contains %d blocks' % (len(self.index_alice)))

        rep_vals_in_clust_alice, self.alice_rep_index = \
            self.__select_rep_ref_vals__(self.index_alice, self.ref_ind_dict_alice)
        for rep_val in rep_vals_in_clust_alice:
            self.alice_rep_vals.append(self.ref_ind_dict_alice[rep_val])
        alice_time = time.time() - start_time
        # print sorted(self.alice_rep_vals)
        # print self.alice_rep_index

        stat = self.block_stats(self.index_alice)
        min_block_size, med_blk_size, max_block_size, avr_block_size, std_dev, blk_len_list = stat

        wr_file_name = './logs/SNN_2P_alice.csv'
        wr_file = open(wr_file_name, 'a')

        sum = 0.0
        for i in blk_len_list:
            sum = sum + (i - avr_block_size) * (i - avr_block_size)
            wr_file.write(str(i) + ',')
        wr_file.write(os.linesep)
        wr_file.close()

        return min_block_size, med_blk_size, max_block_size, avr_block_size, std_dev, alice_time

    # --------------------------------------------------------------------------

    def build_index_bob(self, attr_select_list):
        """Build the index for Bob assuming the sorted reference values have
       been generated.

       Argument:
       - attr_select_list  A list of column numbers that will be used to
                           extract attribute values from the given records,
                           and concatenate them into one string value which is
                           then used as reference value (and added to the
                           result list if it differs from all other reference
                           values).
    """

        start_time = time.time()

        self.attr_select_list_bob = attr_select_list

        self.__sort_ref_values_bob__()
        # self.__sort_appropriate_ref_values_bob__()

        assert self.rec_dict_bob != None
        # print self.sort_ref_val_list_bob
        self.index_bob = self.__generate_sorted_index__(self.rec_dict_bob,
                                                        attr_select_list, self.sort_ref_val_list_bob,
                                                        self.ref_ind_dict_bob)

        print('Index for Bob contains %d blocks' % (len(self.index_bob)))

        rep_vals_in_clust_bob, self.bob_rep_index = \
            self.__select_rep_ref_vals__(self.index_bob, self.ref_ind_dict_bob)
        for rep_val in rep_vals_in_clust_bob:
            self.bob_rep_vals.append(self.ref_ind_dict_bob[rep_val])
        bob_time = time.time() - start_time

        stat = self.block_stats(self.index_bob)
        min_block_size, med_blk_size, max_block_size, avr_block_size, std_dev, blk_len_list = stat

        wr_file_name = './logs/SNN_2P_bob.csv'
        wr_file = open(wr_file_name, 'a')

        sum = 0.0
        for i in blk_len_list:
            sum = sum + (i - avr_block_size) * (i - avr_block_size)
            wr_file.write(str(i) + ',')
        wr_file.write(os.linesep)
        wr_file.close()

        return min_block_size, med_blk_size, max_block_size, avr_block_size, std_dev, bob_time

    # --------------------------------------------------------------------------

    def generate_blocks(self):
        """Method which generates the blocks based on the built two index data
       structures.
    """

        block_dict = {}  # contains final candidate record pairs

        index_alice = self.index_alice
        index_bob = self.index_bob
        alice_rep_index = self.alice_rep_index
        bob_rep_index = self.bob_rep_index
        k = self.k
        w = self.w
        alice_rep_vals = self.alice_rep_vals
        bob_rep_vals = self.bob_rep_vals

        cand_ref_list = []

        start_time = time.time()

        rep_val_list = set(alice_rep_vals)
        rep_val_list |= set(bob_rep_vals)

        # rep_val_list = alice_rep_vals + bob_rep_vals

        rep_val_list = sorted(list(rep_val_list))

        if SORTED_FIRST_VAL in rep_val_list:
            rep_val_list.remove(SORTED_FIRST_VAL)

        skip = w * 2
        for each in self.__window__(rep_val_list, skip):
            # print list(each)

            num_alice_ref = 0
            num_bob_ref = 0
            this_win_alice_ref = []
            this_win_bob_ref = []

            this_window_list = list(each)
            for val in this_window_list:
                if val in alice_rep_vals:
                    num_alice_ref += 1
                    if val not in this_win_alice_ref:
                        this_win_alice_ref.append(val)
                if val in bob_rep_vals:
                    num_bob_ref += 1
                    if val not in this_win_bob_ref:
                        this_win_bob_ref.append(val)

            while num_alice_ref < w or num_bob_ref < w:
                # print 'skip'
                last_ele_this_list = this_window_list[-1]
                current_pos = rep_val_list.index(last_ele_this_list)
                if current_pos + 1 < len(rep_val_list):
                    next_element = rep_val_list[current_pos + 1]
                    this_window_list.append(next_element)
                    # print this_window_list
                    if next_element in alice_rep_vals:
                        num_alice_ref += 1
                        if next_element not in this_win_alice_ref:
                            this_win_alice_ref.append(next_element)
                    if next_element in bob_rep_vals:
                        num_bob_ref += 1
                        if next_element not in this_win_bob_ref:
                            this_win_bob_ref.append(next_element)
                    # print next_element
                else:
                    break

            # print this_win_alice_ref
            # print this_win_bob_ref

            for this_alice_ref in this_win_alice_ref:
                for this_bob_ref in this_win_bob_ref:
                    if [this_alice_ref, this_bob_ref] not in cand_ref_list:
                        cand_ref_list.append([this_alice_ref, this_bob_ref])

        # print cand_ref_list
        # print rep_val_list

        cand_blk_key = 0
        for cand_pair in cand_ref_list:
            alice_rep, bob_rep = cand_pair

            alice_block = alice_rep_index[alice_rep]
            alice_rec_ids = index_alice[alice_block]

            bob_block = bob_rep_index[bob_rep]
            bob_rec_ids = index_bob[bob_block]

            block_dict[cand_blk_key] = (alice_rec_ids, bob_rec_ids)
            cand_blk_key += 1

        block_time = time.time() - start_time
        # print block_dict
        self.block_dict = block_dict
        print('Final indexing contains %d blocks' % (len(block_dict)))
        return len(block_dict), block_time
