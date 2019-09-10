from argparse import (
    ArgumentParser,
    Namespace,
    _SubParsersAction,
)
import os
from pathlib import (
    Path,
)
import sys
import shutil
import time
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Sequence,
    Tuple,
)

from eth_typing import BLSPubkey

from eth_utils import (
    humanize_seconds,
    to_int,
)
from ruamel.yaml import (
    YAML,
)
from ssz.tools import (
    to_formatted_dict,
)

from eth2._utils.hash import (
    hash_eth2,
)
from eth2.beacon.state_machines.forks.skeleton_lake import MINIMAL_SERENITY_CONFIG
from eth2.beacon.tools.builder.initializer import (
    create_mock_genesis,
)
from eth2.beacon.tools.misc.ssz_vector import (
    override_lengths,
)
from eth2.beacon.typing import (
    Second,
    Timestamp,
)
from eth2._utils.bls import bls
from trinity._utils.shellart import (
    bold_green,
)
from trinity.config import (
    TrinityConfig,
    BeaconAppConfig,
)
from trinity.extensibility import (
    BaseMainProcessPlugin,
)
import ssz

from eth2.beacon.types.states import BeaconState

from trinity.plugins.eth2.network_generator.constants import (
    GENESIS_FILE,
    KEYS_DIR,
)

from trinity.plugins.builtin.network_db.plugin import TrackingBackend


class InteropPlugin(BaseMainProcessPlugin):
    @property
    def name(self) -> str:
        return "Interop"

    @classmethod
    def configure_parser(cls, arg_parser: ArgumentParser, subparser: _SubParsersAction) -> None:

        interop_parser = subparser.add_parser(
            'interop',
            help='Run with a hard-coded configuration',
        )

        time_group = interop_parser.add_mutually_exclusive_group(
            required=True,
        )
        time_group.add_argument(
            '--start-time',
            help="Unix timestamp to use as genesis start time",
            type=int,
        )
        time_group.add_argument(
            '--start-delay',
            help="How many seconds until the genesis is active",
            type=int,
        )

        interop_parser.add_argument(
            '--validators',
            help="Which validators should run",
            type=str,
        )

        interop_parser.add_argument(
            '--wipedb',
            help="Blows away the chaindb so we can start afresh",
            action='store_true',
        )

        interop_parser.set_defaults(munge_func=cls.munge_all_args)

    @classmethod
    def munge_all_args(cls, args: Namespace, trinity_config: TrinityConfig) -> None:
        logger = cls.get_logger()
        logger.info("Configuring testnet")

        override_lengths(MINIMAL_SERENITY_CONFIG)

        if args.wipedb:
            beacon_config = trinity_config.get_app_config(BeaconAppConfig)
            logger.info(f'Blowing away the database: {beacon_config.database_dir}')
            try:
                shutil.rmtree(beacon_config.database_dir)
            except FileNotFoundError:
                # there's nothing to wipe, that's fine!
                pass
            else:
                beacon_config.database_dir.mkdir()

        genesis_path = Path('genesis.ssz')
        logger.info(f"Using genesis from {genesis_path}")

        # read the genesis!
        with open(genesis_path, 'rb') as f:
            encoded = f.read()
        state = ssz.decode(encoded, sedes=BeaconState)

        now = int(time.time())
        if args.start_time:
            if args.start_time <= now:
                logger.info(f"--start-time must be a time in the future. Current time is {now}")
                sys.exit(1)

            delta = args.start_time - now
            logger.info(f"Time will begin {delta} seconds from now")

            # adapt the state, then print the new root!
            state = state.copy(
                genesis_time=args.start_time
            )
        elif args.start_delay:
            if args.start_delay < 0:
                logger.info(f"--start-time must be positive")
                sys.exit(1)

            start_time = now + args.start_delay
            logger.info(f"Genesis time is {start_time}")

            state = state.copy(
                genesis_time=start_time
            )
        else:
            logger.error("Could not determine when time begins")
            sys.exit(1)

        logger.info(f"Genesis hash tree root: {state.hash_tree_root.hex()}")

        validators = args.validators
        if not validators:
            logger.info(f"Not running any validators")
        else:
            validators = [int(token) for token in validators.split(',')]
            for validator in validators:
                if validator < 0 or validator > 15:
                    logger.error(f"{validator} is not a valid validator")
                    sys.exit(1)
            logger.info(f"Validating: {validators}")

        logger.info(f"Configuring {trinity_config.trinity_root_dir}")

        # Save the genesis state to the data dir!
        yaml = YAML(typ='unsafe')
        with open(trinity_config.trinity_root_dir / GENESIS_FILE, 'w') as f:
            yaml.dump(to_formatted_dict(state), f)

        # Save the validator keys to the data dir
        keys_dir = trinity_config.trinity_root_dir / KEYS_DIR
        try:
            shutil.rmtree(keys_dir)
        except FileNotFoundError:
            pass
        keys_dir.mkdir()

        # parse the yaml...
        yaml = YAML(typ="unsafe")
        keys = yaml.load(Path('eth2/beacon/scripts/quickstart_state/keygen_16_validators.yaml'))

        # the reverse of extract_privkeys_from_dir
        # a near-copy of generate_keys from the network_generator plugin
        if validators:
            for validator_index in validators:
                key = keys[validator_index]
                file_name = f"v{validator_index:07d}.privkey"
                key_path = keys_dir / file_name
                with open(key_path, "w") as f:
                    f.write(str(to_int(hexstr=key['privkey'])))

        # disable some plugins which shouldn't be running
        args.disable_discovery = True
        args.disable_upnp = True
        args.network_tracking_backend = TrackingBackend.do_not_track
